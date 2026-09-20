"""群组服务：含 AI 自主讨论 + 拉人。"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.group import Group, GroupMember, GroupMessage
from app.ai.llm.factory import get_llm_client_for_user


class GroupService:

    # ==================== 基础操作 ====================

    def create_group(
        self, db: Session, owner_id: int, name: str, member_ids: list[int],
    ) -> dict:
        if not name.strip():
            raise ValueError("群名不能为空")

        group = Group(name=name.strip()[:30], owner_id=owner_id)
        db.add(group)
        db.commit()
        db.refresh(group)

        all_ids = set(member_ids) | {owner_id}
        for uid in all_ids:
            u = db.query(User).filter(User.id == uid).first()
            if u:
                db.add(GroupMember(group_id=group.id, user_id=uid))
        db.commit()

        return self._to_group_dict(db, group)

    def add_members(self, db: Session, group_id: int, owner_id: int, member_ids: list[int]) -> dict:
        """拉人进群（只有群主能操作）。"""
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise ValueError("群不存在")
        if group.owner_id != owner_id:
            raise ValueError("只有群主能拉人")

        added = []
        for uid in member_ids:
            exists = (
                db.query(GroupMember)
                .filter(GroupMember.group_id == group_id, GroupMember.user_id == uid)
                .first()
            )
            if exists:
                continue
            u = db.query(User).filter(User.id == uid).first()
            if not u:
                continue
            db.add(GroupMember(group_id=group_id, user_id=uid))
            added.append(u.nickname or f"用户{u.id}")
        db.commit()

        return {"added_count": len(added), "added_names": added}

    def list_groups(self, db: Session, user_id: int) -> list[dict]:
        member_rows = db.query(GroupMember).filter(GroupMember.user_id == user_id).all()
        group_ids = [m.group_id for m in member_rows]
        groups = db.query(Group).filter(Group.id.in_(group_ids)).order_by(Group.created_at.desc()).all()
        return [self._to_group_dict(db, g) for g in groups]

    def get_group_detail(self, db: Session, group_id: int, user_id: int) -> dict:
        if not self._is_member(db, group_id, user_id):
            raise ValueError("你不是这个群的成员")

        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise ValueError("群不存在")

        members = self._get_members(db, group_id)
        messages = (
            db.query(GroupMessage)
            .filter(GroupMessage.group_id == group_id)
            .order_by(GroupMessage.created_at.asc())
            .limit(100)
            .all()
        )

        return {
            "group": self._to_group_dict(db, group),
            "members": members,
            "messages": [
                {
                    "id": m.id,
                    "group_id": m.group_id,
                    "from_user_id": m.from_user_id,
                    "from_nickname": self._get_nickname(db, m.from_user_id),
                    "content": m.content,
                    "from_ai": m.from_ai,
                    "created_at": m.created_at,
                }
                for m in messages
            ],
        }

    async def send_message(
        self, db: Session, group_id: int, user_id: int, content: str, use_ai: bool = False,
    ) -> dict:
        if not self._is_member(db, group_id, user_id):
            raise ValueError("你不是这个群的成员")
        if not content.strip():
            raise ValueError("消息不能为空")

        final_content = content.strip()

        if use_ai:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                client = get_llm_client_for_user(db, user_id)
                prompt = f"""你是「{user.nickname}」的 AI 助手。
他刚才在群里说：{content}
请帮他把这句话表达得更清晰、更有礼貌，保持原意，50 字以内。直接输出改写后的内容。"""
                final_content = (await client.chat(prompt)).strip()
            except Exception as e:
                print(f"AI 加工失败：{e}")

        msg = GroupMessage(
            group_id=group_id,
            from_user_id=user_id,
            content=final_content,
            from_ai=use_ai,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        return {
            "id": msg.id,
            "group_id": msg.group_id,
            "from_user_id": msg.from_user_id,
            "from_nickname": self._get_nickname(db, user_id),
            "content": msg.content,
            "from_ai": msg.from_ai,
            "created_at": msg.created_at,
        }

    # ==================== ⭐ AI 自主讨论 ====================

    async def _run_discussion(
        self,
        db: Session,
        group_id: int,
        user_id: int,
        topic: str,
    ) -> dict:
        """让群里所有成员的 AI 轮流发言，AI 自己判断何时结束。

        只管跑完，任务状态由 agent_service 维护。
        """
        if not self._is_member(db, group_id, user_id):
            raise ValueError("你不是这个群的成员")

        members = self._get_members(db, group_id)
        if len(members) < 2:
            raise ValueError("群里至少 2 个人才能讨论")

        try:
            client = get_llm_client_for_user(db, user_id)
        except Exception as e:
            raise ValueError(f"发起人没配置 AI Key：{str(e)}")

        group = db.query(Group).filter(Group.id == group_id).first()
        member_names = [m["nickname"] for m in members]

        history_lines = []
        MAX_ROUNDS = 3
        MAX_TOTAL = 20
        message_count = 0
        ended = False

        try:
            for round_num in range(1, MAX_ROUNDS + 1):
                for member in members:
                    if message_count >= MAX_TOTAL:
                        ended = True
                        break

                    history_text = "\n".join(history_lines[-15:]) if history_lines else "（还没有发言）"

                    prompt = f"""你代表「{member['nickname']}」参加一个群讨论。

话题：{topic}
群成员：{', '.join(member_names)}
当前是第 {round_num} 圈发言。

讨论历史：
{history_text}

要求：
1. 用第一人称代表「{member['nickname']}」发言
2. 简洁表达观点，50 字以内
3. 如果你觉得话题已经聊完，在末尾加 [END]
4. 不要暴露你是 AI
5. 只输出发言内容，不要前缀

「{member['nickname']}」发言："""

                    try:
                        reply = (await client.chat(prompt)).strip()
                    except Exception as e:
                        print(f"AI 发言失败：{e}")
                        continue

                    if not reply:
                        continue

                    reply_ended = "[END]" in reply
                    reply_clean = reply.replace("[END]", "").strip()

                    if reply_clean:
                        msg = GroupMessage(
                            group_id=group_id,
                            from_user_id=member["user_id"],
                            content=reply_clean,
                            from_ai=True,
                        )
                        db.add(msg)
                        db.commit()
                        history_lines.append(f"[{member['nickname']}]: {reply_clean}")
                        message_count += 1

                    if reply_ended:
                        ended = True
                        break

                if ended:
                    break

            # 生成总结
            summary = ""
            if history_lines:
                try:
                    summary_prompt = f"""以下是一个群讨论，话题「{topic}」：

{chr(10).join(history_lines)}

请用 3-5 句话总结讨论要点和结论。直接输出总结内容。"""
                    summary = (await client.chat(summary_prompt)).strip()
                except Exception:
                    summary = "总结生成失败"

                msg = GroupMessage(
                    group_id=group_id,
                    from_user_id=user_id,
                    content=f"📊 **讨论总结**\n{summary}",
                    from_ai=True,
                )
                db.add(msg)
                db.commit()

            return {
                "message_count": message_count,
                "summary": summary,
                "ended": ended,
            }

        except Exception as e:
            raise ValueError(f"讨论失败：{str(e)}")

    # ==================== 内部方法 ====================

    def _is_member(self, db: Session, group_id: int, user_id: int) -> bool:
        return (
            db.query(GroupMember)
            .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
            .first()
        ) is not None

    def _get_members(self, db: Session, group_id: int) -> list[dict]:
        rows = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
        result = []
        for r in rows:
            u = db.query(User).filter(User.id == r.user_id).first()
            if u:
                result.append({
                    "user_id": u.id,
                    "nickname": u.nickname or f"用户{u.id}",
                    "avatar": u.avatar,
                })
        return result

    def _get_nickname(self, db: Session, user_id: int) -> str:
        u = db.query(User).filter(User.id == user_id).first()
        return (u.nickname if u else f"用户{user_id}") or "神秘用户"

    def _to_group_dict(self, db: Session, g: Group) -> dict:
        count = db.query(GroupMember).filter(GroupMember.group_id == g.id).count()
        return {
            "id": g.id,
            "name": g.name,
            "owner_id": g.owner_id,
            "member_count": count,
            "created_at": g.created_at,
        }


group_service = GroupService()