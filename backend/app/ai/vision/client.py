"""视觉模型客户端：每个用户用自己的配置。"""
import base64

import httpx

from app.core.logging import get_logger


logger = get_logger(__name__)


class VisionClient:
    def __init__(self, api_key: str, base_url: str, model: str, mock: bool = False):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.mock = mock

    async def describe_image(self, image_path: str, prompt: str = "请描述这张图片的内容") -> str:
        if self.mock:
            import os
            size_kb = round(os.path.getsize(image_path) / 1024, 1)
            return (
                f"【Mock模式 · 视觉】我看到了你上传的图片！\n"
                f"图片大小：{size_kb} KB\n"
                f"你的提问：{prompt}\n"
                f"（配置真实视觉模型 API 后，这里会是 AI 对图片内容的描述）"
            )

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        ext = image_path.rsplit(".", 1)[-1].lower()
        mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
                ]
            }],
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            if resp.status_code != 200:
                logger.error("Vision API 错误: %s - %s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]