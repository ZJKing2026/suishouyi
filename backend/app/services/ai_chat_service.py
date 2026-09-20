"""AI 自主对话服务：两个 AI 围绕话题聊天，AI 自己判断何时结束。"""
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_message import UserMessage
from app.models.ai_chat_task import AIChatTask
from app.ai.llm.factory import get_llm_client_for_user


# 安全上限：防止 AI 一直聊下去烧 token
SAFETY_MAX_ROUNDS = 20


class AIChatService:

    async def start_chat(
        self,
        db: Session,
        user_id: int,
        friend_id: int,
        topic: str,
    ) -> dict:
        """启动一次 AI 自主对话。AI 自己判断何时结束。"""
        # 检查好友关系
        from app.services.friend_service import friend_service
        if not friend_service.are_friends(db, user_id, friend_id):
            raise ValueError("你们不是好友")

        a = db.query(User).filter(User.id == user_id).first()
        b = db.query(User).filter(User.id == friend_id).first()
        if not a or not b:
            raise ValueError("用户不存在")

        # 建任务
        task = AIChatTask(
            user_a_id=user_id,
            user_b_id=friend_id,
            topic=topic,
            max_rounds=SAFETY_MAX_ROUNDS,
            status="running",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 让两个 AI 轮番说
        history_lines = []      # 累积对话记录（纯文本，给 LLM 看）

        try:
            for round_num in range(1, SAFETY_MAX_ROUNDS + 1):
                # A 的 AI 说
                a_reply = await self._generate(
                    db, a, b, topic, history_lines, "a"
                )
                if not a_reply:
                    break

                # 判断是否结束
                a_ended = "[END]" in a_reply
                a_reply_clean = a_reply.replace("[END]", "").strip()

                if a_reply_clean:
                    history_lines.append(f"[{a.nickname}]: {a_reply_clean}")
                    friend_service.send_message(
                        db, from_user_id=user_id, to_user_id=friend_id,
                        content=a_reply_clean, from_ai=True, task_id=task.id,
                    )

                task.current_round = round_num
                db.commit()

                if a_ended:
                    print(f"✅ AI 对话第 {round_num} 轮结束（A 判断）")
                    break

                # B 的 AI 回
                b_reply = await self._generate(
                    db, b, a, topic, history_lines, "b"
                )
                if not b_reply:
                    break

                b_ended = "[END]" in b_reply
                b_reply_clean = b_reply.replace("[END]", "").strip()

                if b_reply_clean:
                    history_lines.append(f"[{b.nickname}]: {b_reply_clean}")
                    friend_service.send_message(
                        db, from_user_id=friend_id, to_user_id=user_id,
                        content=b_reply_clean, from_ai=True, task_id=task.id,
                    )

                db.commit()

                if b_ended:
                    print(f"✅ AI 对话第 {round_num} 轮结束（B 判断）")
                    break
            else:
                # for-else: 循环跑满 20 轮没 break
                print(f"⚠️ AI 对话达到安全上限 {SAFETY_MAX_ROUNDS} 轮")

            # 生成总结
            if history_lines:
                summary = await self._summarize(db, user_id, topic, history_lines)
            else:
                summary = "对话未产生任何内容。"

            task.summary = summary
            task.status = "done"
            task.finished_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            task.status = "failed"
            task.summary = f"对话失败：{str(e)}"
            db.commit()
            raise

        return self._to_response(db, task)

    async def _generate(
        self,
        db: Session,
        speaker: User,
        other: User,
        topic: str,
        history: list[str],
        side: str,
    ) -> str:
        """让某个 AI 生成一句话，允许 AI 判断结束。"""
        try:
            client = get_llm_client_for_user(db, speaker.id)
        except Exception as e:
            print(f"❌ AI client 创建失败：{e}")
            return ""

        history_text = "\n".join(history[-20:]) if history else "（还没有对话）"

        prompt = f"""你是「{speaker.nickname}」的 AI 代理，正在和「{other.nickname}」的 AI 代表他本人对话。

话题：{topic}

对话历史：
{history_text}

要求：
1. 你代表「{speaker.nickname}」的立场说话，但**不要冒充本人**
2. 围绕话题，简洁表达观点，50 字以内
3. **判断是否应该结束对话**：
   - 如果对话已经得出结论
   - 或者再聊下去没有新信息
   - 或者双方都表达了核心观点
   - 或者对方明显不想继续
   → 在回复末尾加上 [END] 标记
4. 否则继续正常对话
5. **绝不编造事实**：你不知道主人的日程、行程、联系方式，
   这类问题一律回答"这个我得先跟他本人确认一下"，不要瞎猜
6. 只输出你说的话，不要任何前缀、解释、旁白

现在，{speaker.nickname} 的 AI 代理说话："""

        try:
            reply = await client.chat(prompt)
            return reply.strip()
        except Exception as e:
            print(f"AI 生成失败：{e}")
            return ""

    async def _summarize(
        self, db: Session, user_id: int, topic: str, history: list[str],
    ) -> str:
        """生成对话总结。"""
        if not history:
            return "对话未产生任何内容。"

        try:
            client = get_llm_client_for_user(db, user_id)
            history_text = "\n".join(history)
            prompt = f"""以下是一场 AI 代理对话的记录，话题是「{topic}」。

{history_text}

请用 3-5 句话总结这场对话的要点，说明双方表达了什么观点，最后达成了什么结论。
直接输出总结，不要加"总结："之类的前缀。"""
            summary = await client.chat(prompt)
            return summary.strip()
        except Exception as e:
            return f"总结生成失败：{str(e)}"

    def _to_response(self, db: Session, task: AIChatTask) -> dict:
        """把任务转成响应（含完整对话记录）。"""
        # 按 task_id 精确取本次任务的记录，避免同一对好友的多次对话互相串台
        msgs = (
            db.query(UserMessage)
            .filter(UserMessage.task_id == task.id)
            .order_by(UserMessage.created_at.asc())
            .all()
        )

        logs = []
        for m in msgs:
            logs.append({
                "speaker": "a" if m.from_user_id == task.user_a_id else "b",
                "content": m.content,
                "round_num": 0,
                "created_at": m.created_at,
            })

        return {
            "id": task.id,
            "user_a_id": task.user_a_id,
            "user_b_id": task.user_b_id,
            "topic": task.topic,
            "status": task.status,
            "current_round": task.current_round,
            "max_rounds": task.max_rounds,
            "summary": task.summary,
            "logs": logs,
            "created_at": task.created_at,
        }

    def get_task(self, db: Session, user_id: int, task_id: int) -> dict:
        task = db.query(AIChatTask).filter(AIChatTask.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        if user_id not in (task.user_a_id, task.user_b_id):
            raise ValueError("无权查看")
        return self._to_response(db, task)


ai_chat_service = AIChatService()