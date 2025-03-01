from pydantic import BaseModel
from typing import Optional
from typing import Optional, List, Dict

class ConfigModel(BaseModel):
    zentao_url: Optional[str] = None
    zentao_username: Optional[str] = None
    zentao_password: Optional[str] = None
    feishu_webhook_url: Optional[str] = None
    fetch_interval: Optional[int] = None
    zentao_token: Optional[str] = None
    selected_product: Optional[str] = None
    selected_product_id: Optional[str] = None

class ProductSelection(BaseModel):
    product_id: str
    product_name: str

class FeishuMessage(BaseModel):
    total: int
    bugs: List[Dict]
    realname: str
    suggestion: Optional[str] = None

