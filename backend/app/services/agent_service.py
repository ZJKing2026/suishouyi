"""AI 代理任务编排：协商、请示、超时的统一状态机。

设计要点：任何需要"等人"的环节都落库挂起，内存里不留悬挂协程。
所以不需要后台调度器，进程重启也不丢任务。
"""
import json
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_config import UserConfig
from app.models.agent_task import (
    AgentTask,
    TYPE_PEER_CONSULT, TYPE_GROUP_DISCUSSION,
    STATUS_RUNNING, STATUS_WAITING_USER, STATUS_WAITING_PEER,
    STATUS_DONE, STATUS_FAILED,
    OUTCOME_ANSWERED, OUTCOME_DECLINED, OUTCOME_PEER_UNAVAILABLE,
    OUTCOME_TIMEOUT, OUTCOME_ERROR,
)
from app.models.agent_request import (
    AgentRequest,
    REQUEST_PENDING, REQUEST_DECIDED,
    ACTION_APPROVE, ACTION_REJECT, ACTION_CUSTOM,
)
from app.ai.llm.factory import get_llm_client_for_user


# 单次协商最多跑几步，防止 AI 之间来回踢皮球
MAX_STEPS = 6

# 请示超过这个时长没人管，自动判超时
REQUEST_TIMEOUT_MINUTES = 10

# 规则预筛：命中这些一律升级到主人，不交给模型判断
ESCALATE_PATTERNS = [
    r"有空|有空吗|时间|日程|安排|几点|什么时候|哪天|周末|明天|后天|下周",
    r"见面|聚|约|来不来|参加|到场|一起吃|一起玩",
    r"答应|承诺|保证|确定|定下来|说好了",
    r"资料|简历|文档|文件|表格|合同|方案|报告|发一份|发给我|传给我",
    r"帮我做|帮我写|帮我生成|帮我准备|帮我处理|帮我查",
    r"多少钱|价格|报价|预算|费用|工资|薪资",
    r"地址|位置|电话|手机号|微信|联系方式|住哪|公司在哪",
    r"身份|身份证|银行卡|密码|验证码",
]

# 规则明确放行：纯社交寒暄，零风险
ALLOW_PATTERNS = [
    r"^你好|^您好|^在吗|^hi|^hello|^嗨|^哈喽",
    r"^谢谢|^多谢|^感谢|^辛苦|^收到|^好的|^好嘞|^ok|^OK",
    r"^再见|^拜拜|^晚安|^早安",
]


class AgentService:

    # ==================== 入口：发起一次协商 ====================

    async def start_peer_consult(
        self, db: Session, owner_id: int, peer_id: int, question: str,
    ) -> dict:
        """发起人让 AI 去问好友。"""
        from app.services.friend_service import friend_service

        question = (question or "").strip()
        if not question:
            raise ValueError("问题不能为空")
        if owner_id == peer_id:
            raise ValueError("不能问自己")
        if not friend_service.are_friends(db, owner_id, peer_id):
            raise ValueError("你们不是好友")

        owner = db.query(User).filter(User.id == owner_id).first()
        peer = db.query(User).filter(User.id == peer_id).first()
        if not owner or not peer:
            raise ValueError("用户不存在")

        task = AgentTask(
            task_type=TYPE_PEER_CONSULT,
            status=STATUS_RUNNING,
            owner_id=owner_id,
            peer_id=peer_id,
            topic=question,
            payload=json.dumps({"question": question}, ensure_ascii=False),
            step_count=1,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 对方没配 Key 就当场收场，不让发起方干等
        if not self._is_agent_available(db, peer_id):
            return self._finish(
                db, task, STATUS_FAILED, OUTCOME_PEER_UNAVAILABLE,
                error=f"「{peer.nickname}」还没有配置 AI Key，暂时联系不上他的 AI",
            )

        # 摆进对方的会话里，让对方知道"你的 AI 替你收到了一条咨询"
        friend_service.send_message(
            db, from_user_id=owner_id, to_user_id=peer_id,
            content=question, from_ai=True, task_id=task.id,
        )

        await self._peer_step(db, task)
        return self.get_task_view(db, task.id, owner_id)

    # ==================== 核心步骤：对方 AI 判断怎么答 ====================

    async def _peer_step(self, db: Session, task: AgentTask) -> None:
        """对方 AI 拿到问题：能答就答，拿不准就请示主人。"""
        from app.services.friend_service import friend_service

        payload = self._load_payload(task)
        question = payload.get("question", "")

        peer = db.query(User).filter(User.id == task.peer_id).first()
        owner = db.query(User).filter(User.id == task.owner_id).first()
        if not peer or not owner:
            self._finish(db, task, STATUS_FAILED, OUTCOME_ERROR, error="用户不存在")
            return

        if not self._is_agent_available(db, task.peer_id):
            self._finish(
                db, task, STATUS_FAILED, OUTCOME_PEER_UNAVAILABLE,
                error="对方 AI 暂时不可用",
            )
            return

        if self._must_escalate(question):
            await self._create_request(db, task, owner, peer, question)
            return

        # 模型再判一次：拿不准的一律升级
        try:
            client = get_llm_client_for_user(db, task.peer_id)
            verdict = await client.chat(self._judge_prompt(peer, owner, question))
        except Exception as e:
            # 判断环节失败，按最保守处理：转人工
            await self._create_request(
                db, task, owner, peer, question,
                note=f"（AI 判断环节出错，已转人工：{str(e)[:60]}）",
            )
            return

        if self._parse_verdict(verdict) == "answer":
            answer = self._strip_json(verdict)
            if not answer:
                await self._create_request(db, task, owner, peer, question)
                return
            friend_service.send_message(
                db, from_user_id=task.peer_id, to_user_id=task.owner_id,
                content=answer, from_ai=True, task_id=task.id,
            )
            self._finish(
                db, task, STATUS_DONE, OUTCOME_ANSWERED,
                result=json.dumps({"answer": answer}, ensure_ascii=False),
            )
            return

        await self._create_request(db, task, owner, peer, question)

    # ==================== 请示 ====================

    async def _create_request(
        self, db: Session, task: AgentTask, owner: User, peer: User,
        question: str, note: str = "",
    ) -> None:
        """建一条请示，任务挂起等主人拍板。"""
        context = await self._gather_context(db, task.peer_id, question)
        suggestion = await self._suggest(db, task.peer_id, owner, question, context)

        req = AgentRequest(
            task_id=task.id,
            requester_id=task.peer_id,
            asker_id=task.owner_id,
            question=question,
            context=note + context if note else context,
            suggestion=suggestion,
            status=REQUEST_PENDING,
        )
        db.add(req)

        task.status = STATUS_WAITING_USER
        task.updated_at = datetime.utcnow()
        db.commit()

    async def _gather_context(self, db: Session, user_id: int, question: str) -> str:
        """给主人看的事实依据：先查知识库，失败了不影响主流程。"""
        try:
            from app.services.rag_service import rag_service, MissingEmbeddingConfigError
        except Exception:
            return ""

        try:
            retrieved = await rag_service._retrieve(db, user_id, question, top_k=3)
        except MissingEmbeddingConfigError:
            return "（未配置知识库，无法自动检索）"
        except Exception:
            return ""

        if not retrieved:
            return "知识库里没有找到相关资料"

        lines = ["资料库中相关内容："]
        for r in retrieved:
            lines.append(f"· {r['content'][:200]}")
        return "\n".join(lines)

    async def _suggest(
        self, db: Session, user_id: int, owner: User, question: str, context: str,
    ) -> str:
        """给主人一条建议，答不出来就算了。"""
        peer = db.query(User).filter(User.id == user_id).first()
        try:
            client = get_llm_client_for_user(db, user_id)
            prompt = f"""你是「{peer.nickname}」的助理。「{owner.nickname}」通过他的助理问：

{question}

你查到的资料：
{context or "（无）"}

请给「{peer.nickname}」一条回复建议，30 字以内，直接输出建议内容。
不要编造资料里没有的事实，拿不准就建议对方说"我先确认一下"。"""
            return (await client.chat(prompt)).strip()[:200]
        except Exception:
            return ""

    # ==================== 决策后恢复 ====================

    async def resolve_request(
        self, db: Session, request_id: int, user_id: int,
        action: str, answer: str = "",
    ) -> dict:
        """主人拍板：批准建议 / 拒绝 / 自己写一句。"""
        from app.services.friend_service import friend_service

        req = db.query(AgentRequest).filter(AgentRequest.id == request_id).first()
        if not req:
            raise ValueError("请示不存在")
        if req.requester_id != user_id:
            raise ValueError("这条请示不是你的")
        if req.status != REQUEST_PENDING:
            raise ValueError("这条请示已经处理过了")

        task = db.query(AgentTask).filter(AgentTask.id == req.task_id).first()
        if not task:
            raise ValueError("关联任务不存在")

        owner = db.query(User).filter(User.id == task.owner_id).first()
        topic = owner.nickname if owner else "对方"

        if action == ACTION_APPROVE:
            final = (req.suggestion or "").strip() or "好的，我这边没问题"
            outcome = OUTCOME_ANSWERED
        elif action == ACTION_REJECT:
            final = await self._decline_reply(db, task.peer_id, topic)
            outcome = OUTCOME_DECLINED
        elif action == ACTION_CUSTOM:
            final = (answer or "").strip()
            if not final:
                raise ValueError("自定义回复不能为空")
            outcome = OUTCOME_ANSWERED
        else:
            raise ValueError(f"未知的操作：{action}")

        req.status = REQUEST_DECIDED
        req.action = action
        req.answer = final
        req.resolved_at = datetime.utcnow()
        db.commit()

        friend_service.send_message(
            db, from_user_id=task.peer_id, to_user_id=task.owner_id,
            content=final, from_ai=True, task_id=task.id,
        )

        self._finish(
            db, task, STATUS_DONE, outcome,
            result=json.dumps({"answer": final}, ensure_ascii=False),
        )

        return self.get_task_view(db, task.id, user_id)

    async def _decline_reply(self, db: Session, user_id: int, topic: str) -> str:
        """拒绝时，让 AI 写得体面一点，措辞失败就用固定话术。"""
        try:
            client = get_llm_client_for_user(db, user_id)
            prompt = f"""「{topic}」通过助理来问一件事，但主人决定不回答。

请写一句得体、不伤感情的回复，20 字以内，不要编造理由，不要暴露是 AI。
例如"我先确认一下再回复你"。直接输出这句话。"""
            reply = (await client.chat(prompt)).strip()
            return reply[:100] or "我先确认一下，稍后回复你"
        except Exception:
            return "我先确认一下，稍后回复你"

    # ==================== 超时与恢复 ====================

    def expire_stale(self, db: Session) -> int:
        """把超时未决策的请示判死，顺带结束它的任务。延迟触发，不需要定时器。"""
        from app.services.friend_service import friend_service

        deadline = datetime.utcnow() - timedelta(minutes=REQUEST_TIMEOUT_MINUTES)
        stale = (
            db.query(AgentRequest)
            .filter(AgentRequest.status == REQUEST_PENDING, AgentRequest.created_at < deadline)
            .all()
        )

        for req in stale:
            req.status = REQUEST_DECIDED
            req.action = "timeout"
            req.answer = ""
            req.resolved_at = datetime.utcnow()

            task = db.query(AgentTask).filter(AgentTask.id == req.task_id).first()
            if task and task.status == STATUS_WAITING_USER:
                self._finish(
                    db, task, STATUS_FAILED, OUTCOME_TIMEOUT,
                    error="超过 10 分钟没有决策，已自动结束",
                )
            db.commit()
        return len(stale)

    def recover_orphans(self, db: Session) -> int:
        """进程重启后，把卡在中间态的任务标记出来，避免永远转圈。"""
        rows = (
            db.query(AgentTask)
            .filter(AgentTask.status.in_([STATUS_RUNNING, STATUS_WAITING_PEER]))
            .all()
        )
        for t in rows:
            self._finish(
                db, t, STATUS_FAILED, OUTCOME_ERROR,
                error="服务重启，任务已中断",
            )
        db.commit()
        return len(rows)

    # ==================== 群讨论 ====================

    async def run_group_discussion(
        self, db: Session, task_id: int,
    ) -> None:
        """
        执行一场群讨论。

        由调用方先建好任务再丢进后台，这里只负责跑完并落库，
        中途不阻塞任何 HTTP 请求。
        """
        from app.services.group_service import group_service

        task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if not task:
            return

        try:
            payload = self._load_payload(task)
            result = await group_service._run_discussion(
                db, task.group_id, task.owner_id, task.topic,
            )
            self._finish(
                db, task, STATUS_DONE, OUTCOME_ANSWERED,
                result=json.dumps(result, ensure_ascii=False),
            )
        except Exception as e:
            self._finish(db, task, STATUS_FAILED, OUTCOME_ERROR, error=str(e))

    def create_group_discussion(
        self, db: Session, group_id: int, user_id: int, topic: str,
    ) -> dict:
        """建一条群讨论任务，返回给前端轮询。"""
        task = AgentTask(
            task_type=TYPE_GROUP_DISCUSSION,
            status=STATUS_RUNNING,
            owner_id=user_id,
            group_id=group_id,
            topic=topic,
            payload=json.dumps({"topic": topic}, ensure_ascii=False),
            step_count=1,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return self.get_task_view(db, task.id, user_id)

    # ==================== 查询 ====================

    def list_pending_requests(self, db: Session, user_id: int) -> list[dict]:
        """待我决策的请示（先顺手清理超时的）。"""
        self.expire_stale(db)

        rows = (
            db.query(AgentRequest)
            .filter(AgentRequest.requester_id == user_id, AgentRequest.status == REQUEST_PENDING)
            .order_by(AgentRequest.created_at.desc())
            .all()
        )
        return [self._to_request_view(db, r) for r in rows]

    def get_task_view(self, db: Session, task_id: int, user_id: int) -> dict:
        task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")

        allowed = user_id in (task.owner_id, task.peer_id)
        if not allowed and task.group_id:
            # 群讨论任务，群成员都能看
            allowed = self._is_group_member(db, task.group_id, user_id)
        if not allowed:
            raise ValueError("无权查看")

        pending = (
            db.query(AgentRequest)
            .filter(AgentRequest.task_id == task.id, AgentRequest.status == REQUEST_PENDING)
            .first()
        )

        return {
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "owner_id": task.owner_id,
            "peer_id": task.peer_id,
            "topic": task.topic,
            "outcome": task.outcome,
            "error": task.error,
            "result": self._load_result(task),
            "pending_request_id": pending.id if pending else None,
            "created_at": task.created_at,
            "finished_at": task.finished_at,
        }

    # ==================== 内部工具 ====================

    def _is_agent_available(self, db: Session, user_id: int) -> bool:
        cfg = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        return bool(cfg and cfg.llm_api_key)

    def _is_group_member(self, db: Session, group_id: int, user_id: int) -> bool:
        from app.models.group import GroupMember

        return (
            db.query(GroupMember)
            .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
            .first()
        ) is not None

    def _must_escalate(self, question: str) -> bool:
        """规则预筛：命中的一律请示，不确定的交给模型。"""
        text = (question or "").strip()
        if not text:
            return True

        for p in ESCALATE_PATTERNS:
            if re.search(p, text):
                return True
        for p in ALLOW_PATTERNS:
            if re.search(p, text, re.IGNORECASE):
                return False
        return False

    def _judge_prompt(self, peer: User, owner: User, question: str) -> str:
        return f"""你是「{peer.nickname}」的私人助理。现在「{owner.nickname}」的助理替他来问一件事：

「{question}」

先判断：这件事你能直接回答，还是必须先请示「{peer.nickname}」本人？

【可以直接回答】只会用到常识、公开信息，或纯社交寒暄。例如：
- 打招呼、谢谢、收到
- 通用的知识性问题
- 帮主人礼貌地拒绝推销

【必须请示主人】只要涉及主人本人的任何信息或决定，一律请示。例如：
- 主人的时间、日程、有没有空
- 主人的隐私、资料、联系方式
- 任何承诺、答应、约定
- 动用主人的资源（发文件、发资料）
- 你拿不准的、资料里没有依据的

最重要的原则：涉及主人本人的事，宁可请示，绝不臆测。
你没有主人的日历、通讯录和行程，任何关于主人的具体回答都是编的。

严格按下面的格式输出，不要有多余内容：
如果你能直接回答，输出：{{"decision": "answer", "reply": "要回复对方的话，50 字以内"}}
如果你需要请示，输出：{{"decision": "escalate"}}
只输出 JSON，不要代码块标记。"""

    def _parse_verdict(self, raw: str) -> str:
        """解析模型的判定，解析不出来一律当 escalate。"""
        text = (raw or "").strip()
        if not text:
            return "escalate"

        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        try:
            data = json.loads(text)
            decision = str(data.get("decision", "")).lower()
            if decision == "answer" and str(data.get("reply", "")).strip():
                return "answer"
            return "escalate"
        except Exception:
            return "escalate"

    def _strip_json(self, raw: str) -> str:
        """从 answer 判定里取出真正要发给对方的话。"""
        text = (raw or "").strip()
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        try:
            data = json.loads(text)
            return str(data.get("reply", "")).strip()
        except Exception:
            return ""

    def _finish(
        self, db: Session, task: AgentTask, status: str, outcome: str,
        result: str = None, error: str = None,
    ) -> dict:
        task.status = status
        task.outcome = outcome
        task.result = result
        task.error = error
        task.finished_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        db.commit()
        return self.get_task_view(db, task.id, task.owner_id)

    def _load_payload(self, task: AgentTask) -> dict:
        try:
            return json.loads(task.payload or "{}")
        except Exception:
            return {}

    def _load_result(self, task: AgentTask) -> dict:
        try:
            return json.loads(task.result or "{}")
        except Exception:
            return {}

    def _to_request_view(self, db: Session, req: AgentRequest) -> dict:
        asker = db.query(User).filter(User.id == req.asker_id).first() if req.asker_id else None
        return {
            "id": req.id,
            "task_id": req.task_id,
            "question": req.question,
            "context": req.context,
            "suggestion": req.suggestion,
            "asker_id": req.asker_id,
            "asker_nickname": (asker.nickname if asker else "对方") or "神秘用户",
            "created_at": req.created_at,
        }


agent_service = AgentService()
