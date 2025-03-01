import os
import json
import datetime
import aiohttp
import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from tenacity import retry, wait_exponential, stop_after_attempt
from ..models.models import FeishuMessage  # 假设有一个 FeishuMessage 模型类

class BugFetcherCore:
    def __init__(self, config_path: str = "config.json"):
        """初始化 BugFetcherCore 类"""
        self.config_path = config_path
        self.user_realname = ""  # 用户真实姓名
        self._config = {}  # 配置缓存
        self._config_mtime = 0  # 配置文件修改时间戳

        # 配置日志
        self.logger = logging.getLogger("BugFetcher")
        self.logger.setLevel(logging.DEBUG)  # 设置日志级别为 DEBUG

        # 初始化时加载配置
        self._load_config()

    def _load_config(self) -> None:
        """智能加载配置，仅在文件修改后重新加载"""
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime != self._config_mtime:
                with open(self.config_path, "r") as f:
                    self._config = json.load(f)
                self._config_mtime = current_mtime
                self.log_message("Configuration reloaded", level=logging.INFO)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_message(f"Config error: {str(e)}", level=logging.ERROR)
            self._config = {}

    ### **属性方法**
    @property
    def zentao_url(self) -> str:
        return self._config.get("zentao_url", "")

    @property
    def zentao_username(self) -> str:
        return self._config.get("zentao_username", "")

    @property
    def zentao_password(self) -> str:
        return self._config.get("zentao_password", "")

    @property
    def feishu_webhook_url(self) -> str:
        return self._config.get("feishu_webhook_url", "")

    @property
    def fetch_interval(self) -> int:
        return self._config.get("fetch_interval", 60)

    @property
    def zentao_token(self) -> str:
        """禅道访问令牌"""
        return self._config.get("zentao_token", "")

    @zentao_token.setter
    def zentao_token(self, value: str):
        """更新令牌"""
        self._config["zentao_token"] = value

    @property
    def selected_product(self) -> str:
        return self._config.get("selected_product", "")

    @property
    def selected_product_id(self) -> str:
        return self._config.get("selected_product_id", "")

    ### **日志和配置管理**
    def log_message(self, message: str, level: int = logging.INFO) -> None:
        """记录日志信息"""
        self.logger.log(level, message)
        # 同时输出到控制台，方便调试
        print(f"{datetime.datetime.now()}: {message}")

    def save_config(self) -> None:
        """保存配置到文件"""
        with open(self.config_path, "w") as f:
            json.dump(self._config, f)
        self._config_mtime = os.path.getmtime(self.config_path)
        self.log_message("Configuration saved", level=logging.INFO)

    ### **核心API请求方法**
    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def api_request(self, method: str, url: str, **kwargs) -> Dict:
        """统一API请求处理方法"""
        headers = kwargs.pop("headers", {})
        if "Token" not in headers and self.zentao_token:
            headers["Token"] = self.zentao_token
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        self.log_message(f"API request: {method} {url}", level=logging.DEBUG)
        self.log_message(f"Headers: {headers}", level=logging.DEBUG)

        try:
            async with aiohttp.ClientSession() as session:
                http_method = getattr(session, method.lower())
                async with http_method(
                    url, headers=headers, timeout=30, **kwargs
                ) as response:
                    self.log_message(f"Response status: {response.status}", level=logging.DEBUG)
                    if response.status in [200, 201]:
                        data = await response.json()
                        return {"status": "success", "data": data}
                    if response.status == 401 and self.zentao_token:
                        self.log_message("Token expired, refreshing", level=logging.WARNING)
                        new_token = await self.get_zentao_token()
                        if new_token:
                            headers["Token"] = new_token
                            return await self.api_request(method, url, headers=headers, **kwargs)
                    response_text = await response.text()
                    self.log_message(f"Error response: {response_text}", level=logging.ERROR)
                    return {"status": "error", "message": response_text, "code": response.status}
        except asyncio.TimeoutError:
            self.log_message("Request timed out", level=logging.ERROR)
            raise
        except aiohttp.ClientError as e:
            self.log_message(f"Request error: {str(e)}", level=logging.ERROR)
            raise

    ### **禅道相关方法**
    async def get_zentao_token(self) -> Optional[str]:
        """获取禅道API访问令牌"""
        self.log_message("Getting ZenTao token", level=logging.INFO)
        login_url = f"{self.zentao_url}/api.php/v1/tokens"
        payload = {"account": self.zentao_username, "password": self.zentao_password}

        result = await self.api_request("post", login_url, json=payload, headers={})
        if result["status"] == "success":
            token = result["data"].get("token")
            if token:
                self.zentao_token = token
                self.save_config()
                self.log_message("Token obtained successfully", level=logging.INFO)
                return token
            else:
                self.log_message(f"Token not found in response: {result['data']}", level=logging.ERROR)
                return None
        self.log_message(f"Failed to get token: {result.get('message', 'Unknown error')}", level=logging.ERROR)
        return None

    async def fetch_user_info(self) -> Dict:
        """获取当前用户信息"""
        if not self.zentao_token:
            self.log_message("No token available, fetching new token", level=logging.WARNING)
            if not await self.get_zentao_token():
                return {"status": "error", "message": "Failed to get token"}

        result = await self.api_request("get", f"{self.zentao_url}/api.php/v1/user")
        if result["status"] == "success":
            user_info = result["data"].get("profile", {})
            self.user_realname = user_info.get("realname", "")
            return {"status": "success", "realname": self.user_realname}
        return result

    async def fetch_products(self) -> List[Dict]:
        """获取产品列表"""
        if not self.zentao_token:
            self.log_message("No token available, fetching new token", level=logging.WARNING)
            if not await self.get_zentao_token():
                return []

        result = await self.api_request("get", f"{self.zentao_url}/api.php/v1/products")
        if result["status"] == "success":
            return result["data"].get("products", [])
        return []

    async def fetch_new_bugs(self) -> Dict:
        """获取未解决的Bug列表"""
        self.log_message("Fetching unresolved bugs", level=logging.INFO)
        if not self.selected_product_id:
            return {"status": "error", "message": "No product selected"}

        if not self.zentao_token:
            self.log_message("No token available, fetching new token", level=logging.WARNING)
            if not await self.get_zentao_token():
                return {"status": "error", "message": "Failed to get token"}

        result = await self.api_request(
            "get",
            f"{self.zentao_url}/api.php/v1/products/{self.selected_product_id}/bugs?limit=1000",
        )
        if result["status"] == "success":
            bugs = result["data"].get("bugs", [])
            self.log_message(f"Total bugs fetched: {len(bugs)}", level=logging.INFO)

            if not self.user_realname:
                await self.fetch_user_info()

            unresolved_bugs = [
                bug
                for bug in bugs
                if bug.get("assignedTo", {}).get("realname", "") == self.user_realname
            ]
            self.log_message(f"Number of unresolved bugs: {len(unresolved_bugs)}", level=logging.INFO)
            return {"status": "success", "bugs": unresolved_bugs}
        return result

    ### **飞书消息发送**
    async def send_to_feishu(self, message: FeishuMessage) -> Dict:
        """发送消息到飞书"""
        if not self.feishu_webhook_url:
            self.log_message("Feishu Webhook URL not set", level=logging.ERROR)
            return {"status": "error", "message": "Feishu Webhook URL not set"}

        bug_list = [
            {"id": bug.get("id", "未知ID"), "title": bug.get("title", "未命名缺陷")}
            for bug in message.bugs
        ]

        feishu_message = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"content": "未解决Bug通知", "tag": "plain_text"}},
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**{message.realname}**，您有 **{message.total}** 个未解决的Bug",
                            "tag": "lark_md",
                        },
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": "\n".join([f"- [{bug['id']}] {bug['title']}" for bug in bug_list]),
                            "tag": "lark_md",
                        },
                    },
                    {
                        "tag": "div",
                        "text": {"content": f"**建议**：{message.suggestion}", "tag": "lark_md"},
                    },
                ],
            },
        }

        self.log_message(f"Sending message to Feishu: {feishu_message}", level=logging.DEBUG)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.feishu_webhook_url,
                    headers={"Content-Type": "application/json"},
                    json=feishu_message,
                    timeout=10,
                ) as response:
                    if response.status == 200:
                        self.log_message("Successfully sent to Feishu", level=logging.INFO)
                        return {"status": "success", "message": "Message sent to Feishu"}
                    text = await response.text()
                    self.log_message(f"Failed to send to Feishu: {text}", level=logging.ERROR)
                    return {"status": "error", "message": f"Failed to send: {text}"}
        except Exception as e:
            self.log_message(f"Error sending to Feishu: {str(e)}", level=logging.ERROR)
            return {"status": "error", "message": str(e)}

    ### **同步方法包装**
    def _sync_wrapper(self, async_func: Callable, *args, **kwargs) -> Any:
        """将异步方法包装为同步方法"""
        return asyncio.run(async_func(*args, **kwargs))

    def get_zentao_token_sync(self) -> Optional[str]:
        """同步获取禅道令牌"""
        return self._sync_wrapper(self.get_zentao_token)

    def fetch_user_info_sync(self) -> Dict:
        """同步获取用户信息"""
        return self._sync_wrapper(self.fetch_user_info)

    def fetch_products_sync(self) -> List[Dict]:
        """同步获取产品列表"""
        return self._sync_wrapper(self.fetch_products)

    def fetch_new_bugs_sync(self) -> Dict:
        """同步获取未解决的Bug"""
        return self._sync_wrapper(self.fetch_new_bugs)

    def send_to_feishu_sync(self, message: FeishuMessage) -> Dict:
        """同步发送消息到飞书"""
        return self._sync_wrapper(self.send_to_feishu, message)