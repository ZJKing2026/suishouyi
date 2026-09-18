"""OpenAPI 解析服务：把 OpenAPI / Swagger 规范转成工具列表。"""
import json
import re
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.models.tool import Tool
from app.services.tool_service import is_safe_url


MAX_TOOLS_PER_IMPORT = 50     # 单次最多导入 50 个工具


class OpenApiService:

    # ==================== 主入口：解析 ====================
    async def parse_spec(self, spec: dict | str, url: str | None = None) -> list[dict]:
        """
        解析 OpenAPI / Swagger spec，返回工具列表。
        spec 可以是 dict，也可以是 JSON 字符串。
        url 用于推断 base_url（如果 spec 里没写）。
        """
        if isinstance(spec, str):
            try:
                spec = json.loads(spec)
            except json.JSONDecodeError:
                raise ValueError("JSON 格式错误，请检查你粘贴的内容")

        if not isinstance(spec, dict):
            raise ValueError("OpenAPI 文档必须是一个对象")

        # 判断版本
        is_openapi3 = "openapi" in spec and spec["openapi"].startswith("3")
        is_swagger2 = "swagger" in spec and spec["swagger"].startswith("2")

        if not (is_openapi3 or is_swagger2):
            raise ValueError("不是有效的 OpenAPI 3.x 或 Swagger 2.0 文档")

        # 获取 base_url
        base_url = self._extract_base_url(spec, url)

        # 遍历 paths
        paths = spec.get("paths", {})
        if not paths:
            raise ValueError("OpenAPI 文档里没有任何接口（paths 为空）")

        tools = []
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue
                if not isinstance(operation, dict):
                    continue

                tool = self._build_tool(
                    base_url=base_url,
                    path=path,
                    method=method.upper(),
                    operation=operation,
                    spec=spec,
                    is_openapi3=is_openapi3,
                )
                tools.append(tool)

                if len(tools) >= MAX_TOOLS_PER_IMPORT:
                    break
            if len(tools) >= MAX_TOOLS_PER_IMPORT:
                break

        if not tools:
            raise ValueError("没有解析出任何可用接口")

        return tools

    # ==================== 提取 base_url ====================
    def _extract_base_url(self, spec: dict, url: str | None) -> str:
        # OpenAPI 3.x
        if "servers" in spec and isinstance(spec["servers"], list) and spec["servers"]:
            server_url = spec["servers"][0].get("url", "")
            if server_url.startswith("http"):
                return server_url.rstrip("/")

        # Swagger 2.0
        if "host" in spec:
            scheme = (spec.get("schemes") or ["https"])[0]
            host = spec["host"]
            base_path = spec.get("basePath", "")
            return f"{scheme}://{host}{base_path}".rstrip("/")

        # 从用户提供的 url 推断
        if url:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"

        raise ValueError("无法确定 API 的 Base URL（spec 里没有 servers 或 host）")

    # ==================== 组装单个工具 ====================
    def _build_tool(
        self,
        base_url: str,
        path: str,
        method: str,
        operation: dict,
        spec: dict,
        is_openapi3: bool,
    ) -> dict:
        # 工具名：优先 operationId，否则从 method + path 生成
        raw_name = operation.get("operationId") or self._gen_name(method, path)
        name = self._sanitize_name(raw_name)

        # 描述
        description = (
            operation.get("summary")
            or operation.get("description")
            or f"{method} {path}"
        )[:400]

        # URL（path 里的 {xxx} 保留，运行时替换）
        api_url = base_url + path

        # 参数 schema
        parameters_schema = self._build_parameters_schema(
            operation, spec, is_openapi3,
        )

        # 请求头（默认空，用户需要的话自己加）
        headers = "{}"

        # POST body 模板（如果 requestBody 有 example，可以用）
        body_template = ""

        return {
            "name": name,
            "description": description,
            "api_url": api_url,
            "api_method": method,
            "parameters_schema": json.dumps(parameters_schema, ensure_ascii=False),
            "headers": headers,
            "body_template": body_template,
        }

    def _gen_name(self, method: str, path: str) -> str:
        """从 method + path 生成工具名，如 get_users_by_id。"""
        parts = [method.lower()]
        for seg in path.strip("/").split("/"):
            if seg.startswith("{") and seg.endswith("}"):
                parts.append("by_" + seg[1:-1])
            else:
                parts.append(re.sub(r"[^a-zA-Z0-9_]", "_", seg))
        return "_".join(p for p in parts if p)[:60]

    def _sanitize_name(self, name: str) -> str:
        """工具名只能用字母数字下划线，且不能以数字开头。"""
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        if name and name[0].isdigit():
            name = "op_" + name
        if not name:
            name = "api_call"
        return name[:60]

    # ==================== 参数 Schema ====================
    def _build_parameters_schema(
        self, operation: dict, spec: dict, is_openapi3: bool,
    ) -> dict:
        """把 OpenAPI 的参数和 requestBody 转成 JSON Schema。"""
        properties = {}
        required = []

        # 1. 传统 parameters（query / path / header）
        for param in operation.get("parameters", []) or []:
            # 解析 $ref
            if "$ref" in param:
                param = self._resolve_ref(spec, param["$ref"]) or {}
            if not param:
                continue

            name = param.get("name")
            if not name:
                continue

            # 只处理 query 和 path 参数
            location = param.get("in", "")
            if location not in ("query", "path"):
                continue

            param_schema = param.get("schema") or {}
            prop = self._schema_to_property(param_schema, param.get("description", ""))
            properties[name] = prop

            if param.get("required") or location == "path":
                required.append(name)

        # 2. OpenAPI 3.x requestBody
        if is_openapi3 and "requestBody" in operation:
            body = operation["requestBody"]
            if "$ref" in body:
                body = self._resolve_ref(spec, body["$ref"]) or {}
            content = body.get("content", {})
            # 优先 application/json
            json_content = content.get("application/json") or {}
            body_schema = json_content.get("schema", {})
            if "$ref" in body_schema:
                body_schema = self._resolve_ref(spec, body_schema["$ref"]) or {}

            if body_schema.get("type") == "object":
                for k, v in (body_schema.get("properties") or {}).items():
                    if "$ref" in v:
                        v = self._resolve_ref(spec, v["$ref"]) or {}
                    properties[k] = self._schema_to_property(v, v.get("description", ""))
                for k in body_schema.get("required", []) or []:
                    if k not in required:
                        required.append(k)

        # 3. Swagger 2.0 body 参数
        if not is_openapi3:
            for param in operation.get("parameters", []) or []:
                if param.get("in") == "body" and "schema" in param:
                    schema = param["schema"]
                    if "$ref" in schema:
                        schema = self._resolve_ref(spec, schema["$ref"]) or {}
                    if schema.get("type") == "object":
                        for k, v in (schema.get("properties") or {}).items():
                            properties[k] = self._schema_to_property(v, v.get("description", ""))
                        for k in schema.get("required", []) or []:
                            if k not in required:
                                required.append(k)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def _schema_to_property(self, schema: dict, description: str = "") -> dict:
        """把一个 OpenAPI schema 转成 JSON Schema property。"""
        if not schema:
            return {"type": "string", "description": description}

        t = schema.get("type", "string")
        prop = {"type": t if t in ("string", "number", "integer", "boolean", "array") else "string"}

        if description:
            prop["description"] = description[:200]
        elif schema.get("description"):
            prop["description"] = schema["description"][:200]

        if t == "array" and "items" in schema:
            items = schema["items"]
            prop["items"] = {"type": items.get("type", "string")}

        if "enum" in schema:
            prop["enum"] = schema["enum"]

        return prop

    def _resolve_ref(self, spec: dict, ref: str) -> dict | None:
        """解析 $ref，如 '#/components/schemas/User'。"""
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        obj = spec
        for p in parts:
            if isinstance(obj, dict) and p in obj:
                obj = obj[p]
            else:
                return None
        return obj if isinstance(obj, dict) else None

    # ==================== 从 URL 拉取 spec ====================
    async def fetch_spec_from_url(self, url: str) -> dict:
        ok, err = is_safe_url(url)
        if not ok:
            raise ValueError(err)

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "suishouyi/1.0"})
            if resp.status_code != 200:
                raise ValueError(f"下载失败：HTTP {resp.status_code}")
            try:
                return resp.json()
            except json.JSONDecodeError:
                raise ValueError("下载的内容不是合法 JSON")
        except httpx.TimeoutException:
            raise ValueError("下载超时")
        except Exception as e:
            raise ValueError(f"下载失败：{str(e)}")

    # ==================== 批量导入 ====================
    def import_tools(
        self,
        db: Session,
        user_id: int,
        tools: list[dict],
        prefix: str = "",
    ) -> dict:
        """
        把解析出来的工具批量保存到用户工具表。
        prefix 用于避免工具名冲突，比如 "petstore_"。
        """
        prefix = re.sub(r"[^a-zA-Z0-9_]", "_", prefix)[:20]

        created = []
        skipped = []

        for t in tools:
            full_name = (prefix + t["name"])[:64]

            # 检查重名
            exists = db.query(Tool).filter(
                Tool.user_id == user_id, Tool.name == full_name,
            ).first()
            if exists:
                skipped.append(full_name)
                continue

            tool = Tool(
                user_id=user_id,
                name=full_name,
                description=t["description"],
                parameters_schema=t["parameters_schema"],
                api_url=t["api_url"],
                api_method=t["api_method"],
                headers=t.get("headers", "{}"),
                body_template=t.get("body_template", ""),
                enabled=True,
            )
            db.add(tool)
            created.append(full_name)

        db.commit()

        return {
            "created": len(created),
            "skipped": len(skipped),
            "created_names": created,
            "skipped_names": skipped,
        }


openapi_service = OpenApiService()