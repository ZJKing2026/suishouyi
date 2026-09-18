"""工具业务逻辑：CRUD + 执行。"""
import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.models.tool import Tool


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    """判断 IP 是否属于禁止访问的范围（内网/环回/链路本地/保留/组播）。"""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve_and_check(host: str) -> tuple[bool, str]:
    """
    解析主机名并校验所有返回的 IP，防止域名指向内网绕过字面量检查。

    参数:
        host: 已去掉端口的纯主机名
    返回:
        (是否安全, 错误信息)
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False, "域名无法解析"
    except Exception:
        return False, "域名解析失败"

    if not infos:
        return False, "域名无法解析"

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False, "解析结果不是合法 IP"
        if _is_blocked_ip(ip):
            return False, "禁止访问内网地址"

    return True, ""


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    校验外部工具 URL 是否可安全请求：只允许 http/https，且目标不能落在内网。

    参数:
        url: 待校验的完整 URL
    返回:
        (是否安全, 错误信息)
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 格式错误"
    if parsed.scheme not in ("http", "https"):
        return False, "只支持 http / https"
    host = parsed.hostname
    if not host:
        return False, "URL 缺少主机名"

    host_lower = host.lower().rstrip(".")
    if host_lower in ("localhost", "localhost.localdomain"):
        return False, "禁止访问本机地址"

    # 字面量 IP 直接判断；域名则解析后逐个校验
    try:
        ip = ipaddress.ip_address(host_lower)
    except ValueError:
        return _resolve_and_check(host_lower)

    if _is_blocked_ip(ip):
        return False, "禁止访问内网 IP"
    return True, ""


def _build_final_url(api_url: str, arguments: dict, user_config: dict) -> str:
    """把 user_config 和 arguments 里的 {key} 都替换进 URL。"""
    url = api_url
    for k, v in {**user_config, **arguments}.items():
        url = url.replace("{" + k + "}", str(v))
    return url


def _build_post_body(body_template: str, arguments: dict) -> dict:
    """用 body_template 构造 POST body。{key} 会被 arguments 里的值替换。"""
    if not body_template:
        return arguments
    try:
        # 先把模板里的 {key} 替换成 JSON 字符串值
        text = body_template
        for k, v in arguments.items():
            # 用 json.dumps 处理字符串，转义引号
            replacement = json.dumps(v, ensure_ascii=False)
            if isinstance(v, str):
                # 去掉外层引号（模板里已经有引号包裹）
                replacement = v.replace('"', '\\"').replace("\n", "\\n")
            text = text.replace("{" + k + "}", str(replacement))
        return json.loads(text)
    except Exception:
        return arguments


async def execute_http_tool(tool: Tool, arguments: dict) -> str:
    # 解析用户配置
    try:
        user_config = json.loads(tool.user_config or "{}")
    except Exception:
        user_config = {}

    # 替换 URL 里的占位符
    final_url = _build_final_url(tool.api_url, arguments, user_config)

    # 安全检查
    ok, err = is_safe_url(final_url)
    if not ok:
        return f"错误：{err}"

    # headers
    try:
        headers = json.loads(tool.headers or "{}")
    except json.JSONDecodeError:
        return "错误：headers 不是合法 JSON"

    # 请求
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if tool.api_method.upper() == "GET":
                resp = await client.get(final_url, headers=headers)
            else:
                if tool.body_template:
                    body = _build_post_body(tool.body_template, arguments)
                else:
                    body = arguments
                resp = await client.post(final_url, headers=headers, json=body)

        text = resp.text
        if len(text) > 3000:
            text = text[:3000] + "...(truncated)"

        if resp.status_code >= 400:
            return f"错误：HTTP {resp.status_code} - {text[:500]}"
        return text

    except httpx.TimeoutException:
        return "错误：请求超时（20 秒）"
    except Exception as e:
        return f"错误：{str(e)}"


NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$')


class ToolService:

    def list_tools(self, db: Session, user_id: int) -> list[Tool]:
        return db.query(Tool).filter(Tool.user_id == user_id).order_by(Tool.created_at.desc()).all()

    def list_enabled_tools(self, db: Session, user_id: int) -> list[Tool]:
        return db.query(Tool).filter(Tool.user_id == user_id, Tool.enabled == True).all()

    def get_tool(self, db: Session, user_id: int, tool_id: int) -> Tool | None:
        return db.query(Tool).filter(Tool.user_id == user_id, Tool.id == tool_id).first()

    def get_by_name(self, db: Session, user_id: int, name: str) -> Tool | None:
        return db.query(Tool).filter(Tool.user_id == user_id, Tool.name == name, Tool.enabled == True).first()

    def create_tool(self, db: Session, user_id: int, data: dict) -> Tool:
        name = data["name"].strip()
        if not NAME_PATTERN.match(name):
            raise ValueError("工具名只能用字母、数字、下划线，且不能以数字开头")
        try:
            json.loads(data.get("parameters_schema") or "{}")
        except json.JSONDecodeError:
            raise ValueError("parameters_schema 不是合法 JSON")
        try:
            json.loads(data.get("headers") or "{}")
        except json.JSONDecodeError:
            raise ValueError("headers 不是合法 JSON")

        ok, err = is_safe_url(data["api_url"])
        if not ok:
            raise ValueError(err)

        existing = db.query(Tool).filter(Tool.user_id == user_id, Tool.name == name).first()
        if existing:
            raise ValueError(f"工具名 '{name}' 已存在")

        tool = Tool(
            user_id=user_id,
            name=name,
            description=data["description"],
            parameters_schema=data["parameters_schema"],
            api_url=data["api_url"],
            api_method=data["api_method"].upper(),
            headers=data.get("headers") or "{}",
            body_template=data.get("body_template") or "",
            enabled=data.get("enabled", True),
        )
        db.add(tool)
        db.commit()
        db.refresh(tool)
        return tool

    def update_tool(self, db: Session, user_id: int, tool_id: int, data: dict) -> Tool:
        tool = self.get_tool(db, user_id, tool_id)
        if not tool:
            raise ValueError("工具不存在")

        name = data["name"].strip()
        if not NAME_PATTERN.match(name):
            raise ValueError("工具名只能用字母、数字、下划线，且不能以数字开头")
        try:
            json.loads(data.get("parameters_schema") or "{}")
        except json.JSONDecodeError:
            raise ValueError("parameters_schema 不是合法 JSON")
        try:
            json.loads(data.get("headers") or "{}")
        except json.JSONDecodeError:
            raise ValueError("headers 不是合法 JSON")

        existing = (
            db.query(Tool)
            .filter(Tool.user_id == user_id, Tool.name == name, Tool.id != tool_id)
            .first()
        )
        if existing:
            raise ValueError(f"工具名 '{name}' 已存在")

        ok, err = is_safe_url(data["api_url"])
        if not ok:
            raise ValueError(err)

        tool.name = name
        tool.description = data["description"]
        tool.parameters_schema = data["parameters_schema"]
        tool.api_url = data["api_url"]
        tool.api_method = data["api_method"].upper()
        tool.headers = data.get("headers") or "{}"
        tool.body_template = data.get("body_template") or ""
        tool.enabled = data.get("enabled", True)
        db.commit()
        db.refresh(tool)
        return tool

    def delete_tool(self, db: Session, user_id: int, tool_id: int) -> bool:
        tool = self.get_tool(db, user_id, tool_id)
        if not tool:
            return False
        db.delete(tool)
        db.commit()
        return True


tool_service = ToolService()