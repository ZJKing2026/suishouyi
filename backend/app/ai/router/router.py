"""AI 路由器：根据意图分发任务，构造 Prompt，调用 LLM。"""
from sqlalchemy.orm import Session

from app.ai.router.intent import intent_classifier
from app.ai.llm.factory import get_llm_client_for_user


PROMPT_TEMPLATES = {
    "text_summary": "请总结以下内容，提取核心要点：\n\n{content}",
    "text_translate": "请将以下内容翻译成英文：\n\n{content}",
    "text_polish": "请对以下内容进行润色，使其更通顺专业：\n\n{content}",
    "text_general": "请处理以下请求：\n\n{content}",
}


class AIRouter:
    async def handle(self, db: Session, user_id: int, content: str) -> dict:
        """核心处理方法：需要传入 db 和 user_id，以读取用户配置。"""

        task_type = intent_classifier.classify(content)
        template = PROMPT_TEMPLATES.get(task_type, PROMPT_TEMPLATES["text_general"])
        prompt = template.format(content=content)

        # 从用户配置创建 client
        client = get_llm_client_for_user(db, user_id)
        result = await client.chat(prompt)

        return {"task_type": task_type, "output": result}


ai_router = AIRouter()