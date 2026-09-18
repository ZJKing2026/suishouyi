"""工具市场：预置工具 seed + 添加逻辑。"""
import json
from sqlalchemy.orm import Session

from app.models.builtin_tool import BuiltinTool
from app.models.tool import Tool


DISPLAY_NAMES = {
    "get_daily_quote": "每日一言",
    "get_60s_news": "今日新闻",
    "read_webpage": "网页阅读",
    "wiki_summary": "维基百科",
    "get_ip_info": "IP 查询",
    "get_global_weather": "全球天气",
    "get_earthquake_info": "全球地震",
    "get_air_quality": "空气质量",
    "get_sunrise_sunset": "日出日落",
    "get_exchange_rate": "实时汇率",
    "search_arxiv": "arXiv 论文",
    "search_pubmed": "PubMed 医学",
    "search_openalex": "OpenAlex 学术",
    "search_crossref": "Crossref 文献",
    "lookup_word": "英文词典",
    "get_github_repo": "GitHub 仓库",
    "get_npm_package": "NPM 包信息",
    "dns_lookup": "DNS 查询",
    "get_country_info": "国家信息",
    "geocode_location": "地理编码",
    "get_public_holidays": "公共假期",
    "search_universities": "大学查询",
    "get_nasa_apod": "NASA 天文图",
    "search_recipe": "食谱搜索",
    # 新增
    "notify_feishu": "飞书通知",
    "notify_dingtalk": "钉钉通知",
    "notify_wecom": "企业微信通知",
    "send_email": "发送邮件",
}


def get_display_name(name: str) -> str:
    return DISPLAY_NAMES.get(name, name)


BUILTIN_TOOLS_SEED = [
    # ========== 原有工具（保持不动，这里省略重复的，只列部分） ==========
    {
        "name": "get_daily_quote",
        "description": "获取一句随机的每日一言（名言、诗句、鼓励语）。",
        "category": "娱乐", "icon": "📖",
        "parameters_schema": json.dumps({"type": "object", "properties": {}, "required": []}),
        "api_url": "https://v1.hitokoto.cn/", "api_method": "GET", "headers": "{}",
        "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_60s_news",
        "description": "获取今日 60 秒读懂世界。",
        "category": "信息", "icon": "📰",
        "parameters_schema": json.dumps({"type": "object", "properties": {}, "required": []}),
        "api_url": "https://60s.viki.moe/v2/60s", "api_method": "GET", "headers": "{}",
        "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "read_webpage",
        "description": "读取指定网页的正文内容。",
        "category": "工具", "icon": "🌐",
        "parameters_schema": json.dumps({"type": "object", "properties": {"url": {"type": "string", "description": "完整 URL"}}, "required": ["url"]}),
        "api_url": "https://r.jina.ai/{url}", "api_method": "GET", "headers": "{}",
        "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "wiki_summary",
        "description": "查询中文维基百科某词条的摘要。",
        "category": "信息", "icon": "📚",
        "parameters_schema": json.dumps({"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}),
        "api_url": "https://zh.wikipedia.org/api/rest_v1/page/summary/{title}", "api_method": "GET", "headers": "{}",
        "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_ip_info",
        "description": "查询指定 IP 地址的归属地信息。",
        "category": "工具", "icon": "📍",
        "parameters_schema": json.dumps({"type": "object", "properties": {"ip": {"type": "string"}}, "required": ["ip"]}),
        "api_url": "https://ipapi.co/{ip}/json/", "api_method": "GET", "headers": "{}",
        "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_global_weather",
        "description": "获取全球任意坐标的实时天气。",
        "category": "信息", "icon": "🌦️",
        "parameters_schema": json.dumps({"type": "object", "properties": {"latitude": {"type": "number"}, "longitude": {"type": "number"}}, "required": ["latitude", "longitude"]}),
        "api_url": "https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_earthquake_info",
        "description": "查询最近一个月全球发生的显著地震。",
        "category": "信息", "icon": "🌍",
        "parameters_schema": json.dumps({"type": "object", "properties": {}, "required": []}),
        "api_url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_air_quality",
        "description": "查询全球空气质量指数（AQI）。",
        "category": "信息", "icon": "💨",
        "parameters_schema": json.dumps({"type": "object", "properties": {}, "required": []}),
        "api_url": "https://api.openaq.org/v2/latest?limit=5", "api_method": "GET", "headers": "{}",
        "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_sunrise_sunset",
        "description": "获取指定经纬度的日出日落时间。",
        "category": "信息", "icon": "🌅",
        "parameters_schema": json.dumps({"type": "object", "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}}, "required": ["lat", "lng"]}),
        "api_url": "https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&formatted=0",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_exchange_rate",
        "description": "获取全球主要货币兑指定基准货币的实时汇率。",
        "category": "信息", "icon": "💱",
        "parameters_schema": json.dumps({"type": "object", "properties": {"base": {"type": "string"}}, "required": ["base"]}),
        "api_url": "https://open.er-api.com/v6/latest/{base}", "api_method": "GET", "headers": "{}",
        "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "search_arxiv",
        "description": "搜索 arXiv 上的预印本论文。",
        "category": "工具", "icon": "📄",
        "parameters_schema": json.dumps({"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        "api_url": "http://export.arxiv.org/api/query?search_query={query}&max_results=3",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "search_pubmed",
        "description": "检索 PubMed 医学论文数据库。",
        "category": "工具", "icon": "🧬",
        "parameters_schema": json.dumps({"type": "object", "properties": {"term": {"type": "string"}}, "required": ["term"]}),
        "api_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retmode=json&retmax=5",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "search_openalex",
        "description": "搜索 OpenAlex 学术数据库。",
        "category": "工具", "icon": "🎓",
        "parameters_schema": json.dumps({"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        "api_url": "https://api.openalex.org/works?search={query}&per_page=3",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "search_crossref",
        "description": "检索 Crossref 学术文献数据库。",
        "category": "工具", "icon": "📚",
        "parameters_schema": json.dumps({"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        "api_url": "https://api.crossref.org/works?query={query}&rows=3",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "lookup_word",
        "description": "查询英文单词的释义、音标、同义词。",
        "category": "工具", "icon": "🔤",
        "parameters_schema": json.dumps({"type": "object", "properties": {"word": {"type": "string"}}, "required": ["word"]}),
        "api_url": "https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_github_repo",
        "description": "查询 GitHub 仓库信息（Star 数、Fork 数等）。",
        "category": "工具", "icon": "🐙",
        "parameters_schema": json.dumps({"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}}, "required": ["owner", "repo"]}),
        "api_url": "https://api.github.com/repos/{owner}/{repo}",
        "api_method": "GET", "headers": "{\"User-Agent\":\"suishouyi\"}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_npm_package",
        "description": "查询 NPM 包的最新版本、描述。",
        "category": "工具", "icon": "📦",
        "parameters_schema": json.dumps({"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}),
        "api_url": "https://registry.npmjs.org/{package}",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "dns_lookup",
        "description": "通过 Google DNS 查询域名的 DNS 记录。",
        "category": "工具", "icon": "🌐",
        "parameters_schema": json.dumps({"type": "object", "properties": {"name": {"type": "string"}, "type": {"type": "string"}}, "required": ["name", "type"]}),
        "api_url": "https://dns.google/resolve?name={name}&type={type}",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_country_info",
        "description": "查询国家的首都、人口、语言、货币。",
        "category": "信息", "icon": "🏳️",
        "parameters_schema": json.dumps({"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
        "api_url": "https://restcountries.com/v3.1/name/{name}",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "geocode_location",
        "description": "把地名转换成经纬度坐标。",
        "category": "工具", "icon": "🗺️",
        "parameters_schema": json.dumps({"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}),
        "api_url": "https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1",
        "api_method": "GET", "headers": "{\"User-Agent\":\"suishouyi\"}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_public_holidays",
        "description": "查询某国某年的公共假期。",
        "category": "信息", "icon": "🎉",
        "parameters_schema": json.dumps({"type": "object", "properties": {"year": {"type": "string"}, "country": {"type": "string"}}, "required": ["year", "country"]}),
        "api_url": "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "search_universities",
        "description": "查询某个国家的大学列表。",
        "category": "信息", "icon": "🎓",
        "parameters_schema": json.dumps({"type": "object", "properties": {"country": {"type": "string"}}, "required": ["country"]}),
        "api_url": "http://universities.hipolabs.com/search?country={country}",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "get_nasa_apod",
        "description": "获取 NASA 每日天文图。",
        "category": "娱乐", "icon": "🌌",
        "parameters_schema": json.dumps({"type": "object", "properties": {}, "required": []}),
        "api_url": "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },
    {
        "name": "search_recipe",
        "description": "搜索食谱和配料（英文菜谱）。",
        "category": "娱乐", "icon": "🍳",
        "parameters_schema": json.dumps({"type": "object", "properties": {"keyword": {"type": "string"}}, "required": ["keyword"]}),
        "api_url": "https://www.themealdb.com/api/json/v1/1/search.php?s={keyword}",
        "api_method": "GET", "headers": "{}", "body_template": "", "user_config_schema": "{}",
    },

    # ========== 🐦 飞书通知 ==========
    {
        "name": "notify_feishu",
        "description": "发送一条文本消息到飞书群。当用户说'给飞书发消息'、'通知飞书群'时调用。",
        "category": "通知", "icon": "🐦",
        "parameters_schema": json.dumps({
            "type": "object",
            "properties": {"message": {"type": "string", "description": "要发送的消息内容"}},
            "required": ["message"]
        }),
        "api_url": "{webhook_url}",
        "api_method": "POST",
        "headers": "{\"Content-Type\":\"application/json\"}",
        "body_template": '{"msg_type":"text","content":{"text":"{message}"}}',
        "user_config_schema": json.dumps({
            "webhook_url": {
                "label": "飞书机器人 Webhook URL",
                "placeholder": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx",
                "help": "在飞书群 → 设置 → 群机器人 → 添加自定义机器人，复制 Webhook 地址"
            }
        }),
    },

    # ========== 📌 钉钉通知 ==========
    {
        "name": "notify_dingtalk",
        "description": "发送一条文本消息到钉钉群。当用户说'给钉钉发消息'、'通知钉钉群'时调用。",
        "category": "通知", "icon": "📌",
        "parameters_schema": json.dumps({
            "type": "object",
            "properties": {"message": {"type": "string", "description": "要发送的消息内容"}},
            "required": ["message"]
        }),
        "api_url": "{webhook_url}",
        "api_method": "POST",
        "headers": "{\"Content-Type\":\"application/json\"}",
        "body_template": '{"msgtype":"text","text":{"content":"{message}"}}',
        "user_config_schema": json.dumps({
            "webhook_url": {
                "label": "钉钉机器人 Webhook URL",
                "placeholder": "https://oapi.dingtalk.com/robot/send?access_token=xxxxx",
                "help": "在钉钉群 → 群设置 → 智能群助手 → 添加机器人，复制 Webhook 地址"
            }
        }),
    },

    # ========== 💼 企业微信通知 ==========
    {
        "name": "notify_wecom",
        "description": "发送一条文本消息到企业微信群。当用户说'给企业微信发消息'、'通知企微群'时调用。",
        "category": "通知", "icon": "💼",
        "parameters_schema": json.dumps({
            "type": "object",
            "properties": {"message": {"type": "string", "description": "要发送的消息内容"}},
            "required": ["message"]
        }),
        "api_url": "{webhook_url}",
        "api_method": "POST",
        "headers": "{\"Content-Type\":\"application/json\"}",
        "body_template": '{"msgtype":"text","text":{"content":"{message}"}}',
        "user_config_schema": json.dumps({
            "webhook_url": {
                "label": "企业微信机器人 Webhook URL",
                "placeholder": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx",
                "help": "在企业微信群 → 群机器人 → 添加，复制 Webhook 地址"
            }
        }),
    },

    # ========== 📧 发送邮件 ==========
    {
        "name": "send_email",
        "description": "发送一封邮件。当用户说'帮我发邮件给 xxx'、'发送邮件'时调用。",
        "category": "通知", "icon": "📧",
        "parameters_schema": json.dumps({
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "收件人邮箱，多个用逗号分隔"},
                "subject": {"type": "string", "description": "邮件主题"},
                "body": {"type": "string", "description": "邮件正文（纯文本）"}
            },
            "required": ["to", "subject", "body"]
        }),
        "api_url": "{backend_url}/api/v1/ext/email/send_internal",
        "api_method": "POST",
        "headers": "{\"Content-Type\":\"application/json\",\"X-Internal-Token\":\"{internal_token}\"}",
        "body_template": '{"email":"{email}","auth_code":"{auth_code}","smtp_host":"{smtp_host}","smtp_port":{smtp_port},"to":"{to}","subject":"{subject}","body":"{body}"}',
        "user_config_schema": json.dumps({
            "email": {"label": "你的邮箱地址", "placeholder": "you@qq.com"},
            "auth_code": {"label": "邮箱授权码（不是登录密码）", "placeholder": "16 位授权码", "help": "QQ 邮箱 → 设置 → 账户 → 开启 SMTP → 生成授权码"},
            "smtp_host": {"label": "SMTP 服务器", "placeholder": "smtp.qq.com"},
            "smtp_port": {"label": "SMTP 端口", "placeholder": "465"}
        }),
    },
]


def seed_builtin_tools(db: Session):
    for item in BUILTIN_TOOLS_SEED:
        existing = db.query(BuiltinTool).filter(BuiltinTool.name == item["name"]).first()
        if existing:
            existing.description = item["description"]
            existing.category = item["category"]
            existing.icon = item["icon"]
            existing.parameters_schema = item["parameters_schema"]
            existing.api_url = item["api_url"]
            existing.api_method = item["api_method"]
            existing.headers = item["headers"]
            existing.body_template = item.get("body_template", "")
            existing.user_config_schema = item.get("user_config_schema", "{}")
            existing.enabled = True
        else:
            db.add(BuiltinTool(
                name=item["name"],
                description=item["description"],
                category=item["category"],
                icon=item["icon"],
                parameters_schema=item["parameters_schema"],
                api_url=item["api_url"],
                api_method=item["api_method"],
                headers=item["headers"],
                body_template=item.get("body_template", ""),
                user_config_schema=item.get("user_config_schema", "{}"),
                enabled=True,
            ))
    db.commit()


class MarketService:

    def list_all(self, db: Session) -> list[dict]:
        tools = db.query(BuiltinTool).filter(BuiltinTool.enabled == True).order_by(BuiltinTool.category, BuiltinTool.id).all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "display_name": get_display_name(t.name),
                "description": t.description,
                "category": t.category,
                "icon": t.icon,
                "parameters_schema": t.parameters_schema,
                "api_url": t.api_url,
                "api_method": t.api_method,
                "user_config_schema": t.user_config_schema or "{}",
            }
            for t in tools
        ]

    def get(self, db: Session, tool_id: int) -> BuiltinTool | None:
        return db.query(BuiltinTool).filter(BuiltinTool.id == tool_id, BuiltinTool.enabled == True).first()

    def add_to_user(
        self,
        db: Session,
        user_id: int,
        builtin_id: int,
        user_config: dict | None = None,
    ) -> Tool:
        builtin = self.get(db, builtin_id)
        if not builtin:
            raise ValueError("工具不存在或已下架")

        existing = db.query(Tool).filter(Tool.user_id == user_id, Tool.name == builtin.name).first()
        if existing:
            raise ValueError("你已经添加过这个工具")

        # 处理特殊配置
        config = user_config or {}
        api_url = builtin.api_url

        # 邮件工具需要拼接 backend URL 和内部 token
        if builtin.name == "send_email":
            from app.core.config import settings
            from app.core.security import get_internal_token

            config["backend_url"] = settings.BACKEND_URL
            config["internal_token"] = get_internal_token()

        tool = Tool(
            user_id=user_id,
            name=builtin.name,
            description=builtin.description,
            parameters_schema=builtin.parameters_schema,
            api_url=api_url,
            api_method=builtin.api_method,
            headers=builtin.headers,
            body_template=builtin.body_template or "",
            user_config=json.dumps(config, ensure_ascii=False),
            enabled=True,
        )
        db.add(tool)
        db.commit()
        db.refresh(tool)
        return tool


market_service = MarketService()