"""LLM 客户端：每个用户用自己的 API Key。"""
import json
import re
import httpx


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, mock: bool = False):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.mock = mock

    # ==================== 单轮对话 ====================
    async def chat(self, prompt: str) -> str:
        if self.mock:
            return f"【Mock模式】收到你的请求啦！如果配置了 API Key，这里会是真实 AI 的回答。\n你的输入是：{prompt[:50]}..."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]

    # ==================== 多轮对话 ====================
    async def chat_with_history(self, messages: list[dict]) -> str:
        if self.mock:
            last_user_msg = ""
            for msg in reversed(messages):
                if msg["role"] == "user":
                    last_user_msg = msg["content"]
                    break
            return (
                f"【Mock模式 · 多轮对话】收到你的第 {len(messages)} 条消息。\n"
                f"你刚才说：{last_user_msg[:60]}...\n"
                f"（配置真实 API Key 后这里会是真正的 AI 回复）"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]

    # ==================== 带工具的对话 ====================
    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        if self.mock:
            return self._mock_tool_decision(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "temperature": 0.7,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            resp.raise_for_status()
            result = resp.json()
            msg = result["choices"][0]["message"]
            return {
                "content": msg.get("content"),
                "tool_calls": msg.get("tool_calls") or [],
            }

    # ==================== Mock 工具决策 ====================
    def _mock_tool_decision(self, messages: list[dict]) -> dict:
        if messages and messages[-1].get("role") == "tool":
            tool_result = messages[-1]["content"]
            return {
                "content": f"【Mock · Agent】根据工具返回的结果：\n{tool_result}",
                "tool_calls": []
            }

        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg["content"]
                break

        if any(k in last_user for k in ["几点", "现在时间", "今天日期", "几号", "星期几"]):
            return {
                "content": None,
                "tool_calls": [{"id": "call_mock_time", "type": "function",
                    "function": {"name": "get_current_time", "arguments": "{}"}}]
            }

        if "天气" in last_user:
            m = re.search(r'([\u4e00-\u9fa5]{2,4})的?天气', last_user)
            city = m.group(1) if m else "北京"
            return {
                "content": None,
                "tool_calls": [{"id": "call_mock_weather", "type": "function",
                    "function": {"name": "get_weather",
                        "arguments": json.dumps({"city": city}, ensure_ascii=False)}}]
            }

        m = re.search(r'(\d+(?:\s*[+\-*/]\s*\d+)+)', last_user)
        if m:
            return {
                "content": None,
                "tool_calls": [{"id": "call_mock_calc", "type": "function",
                    "function": {"name": "calculate",
                        "arguments": json.dumps({"expression": m.group(1).strip()}, ensure_ascii=False)}}]
            }

        return {
            "content": f"【Mock模式】我听到你说：{last_user[:50]}。\n可以问我：现在几点？北京天气？算 23*45+12",
            "tool_calls": []
        }