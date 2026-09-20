"""好友业务逻辑：含 AI 代理问好友。"""
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.friendship import Friendship
from app.models.user_message import UserMessage


class FriendService:

    # ==================== 生成邀请 ====================
    def create_invite(self, db: Session, user_id: int) -> dict:
        existing = (
            db.query(Friendship)
            .filter(
                Friendship.user_id == user_id,
                Friendship.friend_id == None,
                Friendship.status == "pending",
            )
            .first()
        )
        if existing:
            code = existing.invite_code
        else:
            code = Friendship.generate_invite_code()
            invite = Friendship(
                user_id=user_id,
                invite_code=code,
                status="pending",
            )
            db.add(invite)
            db.commit()

        return {
            "invite_code": code,
            "share_path": f"/pages/friends/accept/accept?code={code}",
        }

    # ==================== 查看邀请 ====================
    def get_invite(self, db: Session, code: str, current_user_id: int) -> dict:
        invite = db.query(Friendship).filter(Friendship.invite_code == code).first()
        if not invite:
            raise ValueError("邀请码不存在或已失效")

        inviter = db.query(User).filter(User.id == invite.user_id).first()
        if not inviter:
            raise ValueError("邀请人不存在")

        return {
            "inviter_nickname": inviter.nickname or "神秘用户",
            "inviter_avatar": inviter.avatar,
            "status": invite.status,
            "is_self": invite.user_id == current_user_id,
        }

    # ==================== 接受邀请 ====================
    def accept_invite(self, db: Session, code: str, user_id: int) -> dict:
        invite = db.query(Friendship).filter(Friendship.invite_code == code).first()
        if not invite:
            raise ValueError("邀请码不存在")
        if invite.status != "pending":
            raise ValueError("该邀请已被使用")
        if invite.user_id == user_id:
            raise ValueError("不能加自己为好友")

        existing = (
            db.query(Friendship)
            .filter(
                Friendship.user_id == invite.user_id,
                Friendship.friend_id == user_id,
                Friendship.status == "accepted",
            )
            .first()
        )
        if existing:
            raise ValueError("你们已经是好友了")

        invite.friend_id = user_id
        invite.status = "accepted"
        invite.accepted_at = datetime.utcnow()

        reverse = Friendship(
            user_id=user_id,
            friend_id=invite.user_id,
            status="accepted",
            invite_code=Friendship.generate_invite_code(),
            accepted_at=datetime.utcnow(),
        )
        db.add(reverse)
        db.commit()

        return {"success": True, "message": "已添加为好友"}

    # ==================== 好友列表 ====================
    def list_friends(self, db: Session, user_id: int) -> list[dict]:
        friendships = (
            db.query(Friendship)
            .filter(
                Friendship.user_id == user_id,
                Friendship.status == "accepted",
            )
            .all()
        )

        result = []
        for f in friendships:
            friend = db.query(User).filter(User.id == f.friend_id).first()
            if not friend:
                continue
            result.append({
                "id": f.id,
                "friend_id": friend.id,
                "nickname": friend.nickname or f"用户{friend.id}",
                "avatar": friend.avatar,
                "status": f.status,
                "created_at": f.accepted_at or f.created_at,
            })
        return result

    # ==================== 检查是否好友 ====================
    def are_friends(self, db: Session, user_id: int, other_id: int) -> bool:
        return (
            db.query(Friendship)
            .filter(
                Friendship.user_id == user_id,
                Friendship.friend_id == other_id,
                Friendship.status == "accepted",
            )
            .first()
        ) is not None

    # ==================== 发消息 ====================
    def send_message(
        self,
        db: Session,
        from_user_id: int,
        to_user_id: int,
        content: str,
        from_ai: bool = False,
        task_id: int | None = None,
    ) -> dict:
        if not content or not content.strip():
            raise ValueError("消息内容不能为空")
        if from_user_id == to_user_id:
            raise ValueError("不能给自己发消息")
        if not self.are_friends(db, from_user_id, to_user_id):
            raise ValueError("对方不是你的好友")

        msg = UserMessage(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            content=content.strip(),
            from_ai=from_ai,
            task_id=task_id,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        return {
            "id": msg.id,
            "from_user_id": msg.from_user_id,
            "to_user_id": msg.to_user_id,
            "content": msg.content,
            "is_read": msg.is_read,
            "from_ai": msg.from_ai,
            "created_at": msg.created_at,
        }

    # ==================== 通过昵称找好友 ====================
    def find_friend_by_name(self, db: Session, user_id: int, name: str) -> dict | None:
        friends = self.list_friends(db, user_id)
        name = name.strip()
        # 精确匹配
        for f in friends:
            if f["nickname"] == name:
                return f
        # 模糊匹配
        for f in friends:
            if name in f["nickname"]:
                return f
        return None

    # ==================== 查看会话 ====================
    def get_messages(
        self,
        db: Session,
        user_id: int,
        friend_id: int,
        limit: int = 50,
    ) -> list[dict]:
        msgs = (
            db.query(UserMessage)
            .filter(
                ((UserMessage.from_user_id == user_id) & (UserMessage.to_user_id == friend_id))
                | ((UserMessage.from_user_id == friend_id) & (UserMessage.to_user_id == user_id))
            )
            .order_by(UserMessage.created_at.asc())
            .limit(limit)
            .all()
        )

        # 标记为已读
        for m in msgs:
            if m.to_user_id == user_id and not m.is_read:
                m.is_read = True
        db.commit()

        return [
            {
                "id": m.id,
                "from_user_id": m.from_user_id,
                "to_user_id": m.to_user_id,
                "content": m.content,
                "is_read": m.is_read,
                "from_ai": m.from_ai,
                "created_at": m.created_at,
            }
            for m in msgs
        ]

    # ==================== 未读汇总 ====================
    def get_unread_summary(self, db: Session, user_id: int) -> dict:
        unread_msgs = (
            db.query(UserMessage)
            .filter(
                UserMessage.to_user_id == user_id,
                UserMessage.is_read == False,
            )
            .order_by(UserMessage.created_at.desc())
            .all()
        )

        grouped = {}
        for m in unread_msgs:
            if m.from_user_id not in grouped:
                grouped[m.from_user_id] = []
            grouped[m.from_user_id].append(m)

        summaries = []
        for from_user_id, msgs in grouped.items():
            sender = db.query(User).filter(User.id == from_user_id).first()
            latest = msgs[0]
            summaries.append({
                "from_user_id": from_user_id,
                "nickname": (sender.nickname if sender else f"用户{from_user_id}") or "神秘用户",
                "unread_count": len(msgs),
                "last_content": latest.content[:50],
                "last_time": latest.created_at,
            })

        return {
            "summaries": summaries,
            "total_unread": len(unread_msgs),
        }

    # ==================== ⭐ AI 代理问好友（核心） ====================
    async def ask_friend_via_ai(
        self,
        db: Session,
        user_id: int,
        friend_name: str,
        question: str,
    ) -> dict:
        """
        让 AI 代表用户去问好友。

        走代理任务状态机：对方 AI 能答就直接答，涉及主人本人的事会先请示他本人，
        这时不阻塞等待，直接把"已转人工"的消息返回给调用方。
        """
        from app.services.agent_service import agent_service

        friend = self.find_friend_by_name(db, user_id, friend_name)
        if not friend:
            return {
                "success": False,
                "message": f"没有找到名叫「{friend_name}」的好友",
            }

        task = await agent_service.start_peer_consult(
            db, owner_id=user_id, peer_id=friend["friend_id"], question=question,
        )

        if task["status"] == "waiting_user":
            return {
                "success": True,
                "pending": True,
                "friend_name": friend["nickname"],
                "question": question,
                "answer": f"「{friend['nickname']}」的 AI 说他要先跟本人确认一下，稍后回你。",
            }

        if task["status"] == "failed":
            return {
                "success": False,
                "message": task.get("error") or "对方 AI 暂时联系不上",
            }

        return {
            "success": True,
            "pending": False,
            "friend_name": friend["nickname"],
            "question": question,
            "answer": (task.get("result") or {}).get("answer", ""),
        }


friend_service = FriendService()