"""求职辅助服务：简历优化、JD 匹配、求职信生成。"""
from sqlalchemy.orm import Session

from app.ai.llm.factory import get_llm_client_for_user


class CareerService:

    async def optimize_resume(self, db: Session, user_id: int, resume_text: str) -> str:
        """简历优化建议。"""
        client = get_llm_client_for_user(db, user_id)
        prompt = f"""请阅读以下简历，给出优化建议。

要求：
1. 指出 3-5 个具体问题（用 - 列表）
2. 每个问题给出改进方向
3. 最后给出 1 句话总结

简历内容：
---
{resume_text[:6000]}
---"""
        return await client.chat(prompt)

    async def match_jd(
        self,
        db: Session,
        user_id: int,
        resume_text: str,
        jd_text: str,
    ) -> str:
        """简历与 JD 匹配度分析。"""
        client = get_llm_client_for_user(db, user_id)
        prompt = f"""请对比以下简历和招聘 JD，给出匹配度分析。

要求：
1. 匹配度百分比（0-100%）
2. 3-5 个匹配点
3. 3-5 个需要补充的能力
4. 学习/补充建议

简历：
---
{resume_text[:3000]}
---

JD：
---
{jd_text[:3000]}
---"""
        return await client.chat(prompt)

    async def generate_cover_letter(
        self,
        db: Session,
        user_id: int,
        resume_text: str,
        jd_text: str,
        company: str,
    ) -> str:
        """生成求职信。"""
        client = get_llm_client_for_user(db, user_id)
        prompt = f"""请根据以下信息，生成一封专业的求职信。

公司：{company}

要求：
1. 开头礼貌问候，说明应聘职位
2. 中间段落突出与 JD 匹配的经历和技能
3. 结尾表达期待，附上联系方式
4. 总长度 300-500 字，专业、真诚、不浮夸

简历：
---
{resume_text[:3000]}
---

JD：
---
{jd_text[:3000]}
---"""
        return await client.chat(prompt)


career_service = CareerService()