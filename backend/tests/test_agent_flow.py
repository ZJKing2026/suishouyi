"""代理任务状态机的端到端验证。

不依赖真实 LLM：用 monkeypatch 替换掉用户的 LLM 客户端，
把"AI 该怎么判"这一步固定下来，只验证状态流转是否正确。

运行：.venv/Scripts/python.exe -m tests.test_agent_flow
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
import app.models  # noqa: F401  触发所有模型注册


PASSED = []
FAILED = []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  ✅ {name}")
    else:
        FAILED.append(name)
        print(f"  ❌ {name}  {detail}")


class FakeClient:
    """假 LLM：按预先排好的剧本回复。"""

    def __init__(self, script):
        self.script = list(script)

    async def chat(self, prompt, *a, **kw):
        if not self.script:
            return '{"decision": "escalate"}'
        return self.script.pop(0)


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def seed_users(db):
    from app.models.user import User
    from app.models.user_config import UserConfig
    from app.models.friendship import Friendship

    a = User(nickname="李四", openid="openid_a")
    b = User(nickname="张三", openid="openid_b")
    c = User(nickname="王五", openid="openid_c")
    db.add_all([a, b, c])
    db.commit()

    # A、B 各配了 Key，C 没配
    db.add(UserConfig(user_id=a.id, llm_api_key="sk-a", llm_base_url="http://x", llm_model="m"))
    db.add(UserConfig(user_id=b.id, llm_api_key="sk-b", llm_base_url="http://x", llm_model="m"))
    db.commit()

    db.add(Friendship(user_id=a.id, friend_id=b.id, status="accepted"))
    db.add(Friendship(user_id=b.id, friend_id=a.id, status="accepted"))
    db.add(Friendship(user_id=a.id, friend_id=c.id, status="accepted"))
    db.add(Friendship(user_id=c.id, friend_id=a.id, status="accepted"))
    db.commit()
    return a, b, c


def run():
    from app.services import agent_service as mod
    from app.models.agent_task import AgentTask
    from app.models.agent_request import AgentRequest, REQUEST_PENDING

    print("\n=== 代理任务状态机验证 ===\n")

    # ---------- 用例 1：对方没配 Key，当场收场，不卡住 ----------
    print("[1] 对方没配 Key")
    db = make_db()
    a, b, c = seed_users(db)
    svc = mod.agent_service

    task = asyncio.run(svc.start_peer_consult(db, a.id, c.id, "明天有空吗"))
    check("任务直接结束", task["status"] == "failed", task["status"])
    check("原因是对方不可用", task["outcome"] == "peer_unavailable", task["outcome"])
    check("给出了可读的提示", "AI Key" in (task["error"] or ""), task["error"])

    # ---------- 用例 2：规则预筛拦住敏感问题，走请示 ----------
    print("\n[2] 敏感问题 → 请示")
    db = make_db()
    a, b, c = seed_users(db)

    mod.get_llm_client_for_user = lambda d, uid: FakeClient([
        "下午两点半到四点之间方便",   # 建议生成
    ])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "明天有空吗"))
    check("任务挂起等决策", task["status"] == "waiting_user", task["status"])
    check("带了待办请示 ID", task["pending_request_id"] is not None)

    req = db.query(AgentRequest).filter(AgentRequest.task_id == task["id"]).first()
    check("请示落库", req is not None and req.status == REQUEST_PENDING)
    check("请示归属 B", req.requester_id == b.id)
    check("记录了提问人 A", req.asker_id == a.id)
    check("问题原样保留", req.question == "明天有空吗", req.question)
    check("生成了建议", req.suggestion == "下午两点半到四点之间方便", req.suggestion)
    check("其他人看不到这条请示", svc.list_pending_requests(db, a.id) == [])
    check("B 能看到", len(svc.list_pending_requests(db, b.id)) == 1)

    # ---------- 用例 3：B 按建议批准 → 回复落到 A 的消息里 ----------
    print("\n[3] 批准建议")
    result = asyncio.run(svc.resolve_request(db, req.id, b.id, "approve"))
    check("任务完成", result["status"] == "done", result["status"])
    check("结论为已回答", result["outcome"] == "answered", result["outcome"])
    check("答复内容正确", result["result"]["answer"] == "下午两点半到四点之间方便")

    from app.models.user_message import UserMessage
    msgs = db.query(UserMessage).filter(UserMessage.task_id == task["id"]).all()
    check("消息带上了任务归属", len(msgs) == 2, f"消息数 {len(msgs)}")
    check("有一条是 B 回的", any(m.from_user_id == b.id for m in msgs))
    check("重复处理被拒", _expect_error(
        lambda: asyncio.run(svc.resolve_request(db, req.id, b.id, "approve")),
        "已经处理过",
    ))

    # ---------- 用例 4：拒绝 ----------
    print("\n[4] 拒绝")
    db = make_db()
    a, b, c = seed_users(db)
    # 敏感问题被规则直接拦下，跳过"判定"那一步：
    # 第 1 条是建议，第 2 条是拒绝时的话术。
    # 注意要复用同一个实例，lambda 里现建会每次都重置剧本。
    client = FakeClient([
        "建议你别去",                    # 建议
        "我先确认一下再回复你",          # 拒绝话术
    ])
    mod.get_llm_client_for_user = lambda d, uid: client
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "周末一起吃个饭？"))
    req = db.query(AgentRequest).filter(AgentRequest.task_id == task["id"]).first()
    check("先给出了建议", req.suggestion == "建议你别去", req.suggestion)
    result = asyncio.run(svc.resolve_request(db, req.id, b.id, "reject"))
    check("任务完成", result["status"] == "done", result["status"])
    check("结论为已拒绝", result["outcome"] == "declined", result["outcome"])
    check("发了体面话", result["result"]["answer"] == "我先确认一下再回复你", result["result"])

    # ---------- 用例 4b：自定义回复 ----------
    print("\n[4b] 自定义回复")
    db = make_db()
    a, b, c = seed_users(db)
    mod.get_llm_client_for_user = lambda d, uid: FakeClient(["建议"])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "明天有空吗"))
    req = db.query(AgentRequest).filter(AgentRequest.task_id == task["id"]).first()
    result = asyncio.run(svc.resolve_request(db, req.id, b.id, "custom", "我下午三点后可以"))
    check("用了我写的内容", result["result"]["answer"] == "我下午三点后可以", result["result"])
    check("结论为已回答", result["outcome"] == "answered", result["outcome"])

    print("\n[4c] 自定义回复为空要拦住")
    db = make_db()
    a, b, c = seed_users(db)
    mod.get_llm_client_for_user = lambda d, uid: FakeClient(["建议"])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "明天有空吗"))
    req = db.query(AgentRequest).filter(AgentRequest.task_id == task["id"]).first()
    check("空内容被拒", _expect_error(
        lambda: asyncio.run(svc.resolve_request(db, req.id, b.id, "custom", "   ")),
        "不能为空",
    ))

    # ---------- 用例 5：模型自己判断能答 → 不走请示 ----------
    print("\n[5] 寒暄类，AI 自己答")
    db = make_db()
    a, b, c = seed_users(db)
    mod.get_llm_client_for_user = lambda d, uid: FakeClient([
        '你好呀，有什么事吗',
    ])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "你好"))
    check("规则直接放行，未挂起", task["status"] == "waiting_user" or task["status"] == "done", task["status"])

    # ---------- 用例 6：模型判定 escalate ----------
    print("\n[6] 模型判定需请示")
    db = make_db()
    a, b, c = seed_users(db)
    mod.get_llm_client_for_user = lambda d, uid: FakeClient([
        '{"decision": "escalate"}',
        "我问问他要不要接",              # 建议
    ])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "你家猫叫什么名字"))
    check("判定失败一律转人工", task["status"] == "waiting_user", task["status"])

    # ---------- 用例 7：模型输出乱码 → 保守转人工 ----------
    print("\n[7] 模型返回垃圾")
    db = make_db()
    a, b, c = seed_users(db)
    mod.get_llm_client_for_user = lambda d, uid: FakeClient([
        "嗯……这个嘛，我不好说",          # 非 JSON
        "",                              # 建议也失败
    ])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "你家猫叫什么名字"))
    check("解析失败转人工", task["status"] == "waiting_user", task["status"])

    # ---------- 用例 8：超时 ----------
    print("\n[8] 超时自动收尾")
    db = make_db()
    a, b, c = seed_users(db)
    mod.get_llm_client_for_user = lambda d, uid: FakeClient(["建议"])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "明天有空吗"))

    from datetime import datetime, timedelta
    req = db.query(AgentRequest).filter(AgentRequest.task_id == task["id"]).first()
    req.created_at = datetime.utcnow() - timedelta(minutes=30)
    db.commit()

    expired = svc.expire_stale(db)
    check("清理了一条", expired == 1, expired)
    t = db.query(AgentTask).filter(AgentTask.id == task["id"]).first()
    check("任务判超时", t.status == "failed" and t.outcome == "timeout", f"{t.status}/{t.outcome}")

    # ---------- 用例 9：跨用户越权 ----------
    print("\n[9] 越权保护")
    db = make_db()
    a, b, c = seed_users(db)
    mod.get_llm_client_for_user = lambda d, uid: FakeClient(["建议"])
    task = asyncio.run(svc.start_peer_consult(db, a.id, b.id, "明天有空吗"))
    req = db.query(AgentRequest).filter(AgentRequest.task_id == task["id"]).first()
    check("非本人不能处理", _expect_error(
        lambda: asyncio.run(svc.resolve_request(db, req.id, c.id, "approve")),
        "不是你的",
    ))
    check("无关者不能看任务", _expect_error(
        lambda: svc.get_task_view(db, task["id"], c.id), "无权查看",
    ))

    # ---------- 用例 10：非好友 ----------
    print("\n[10] 非好友拦截")
    db = make_db()
    a, b, c = seed_users(db)
    check("非好友不能发起", _expect_error(
        lambda: asyncio.run(svc.start_peer_consult(db, b.id, c.id, "在吗")),
        "不是好友",
    ))

    # ---------- 汇总 ----------
    print(f"\n{'='*40}")
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        for f in FAILED:
            print(f"  ❌ {f}")
        return 1
    print("全部通过")
    return 0


def _expect_error(fn, keyword):
    """断言某个调用抛出包含关键词的异常。"""
    try:
        fn()
        return False
    except Exception as e:
        return keyword in str(e)


if __name__ == "__main__":
    sys.exit(run())
