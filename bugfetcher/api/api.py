from fastapi import FastAPI, HTTPException
from ..core import BugFetcherCore
from ..models import ConfigModel, ProductSelection, FeishuMessage
import json

app = FastAPI(title="Bug Fetcher API")
fetcher = BugFetcherCore()


@app.get("/api/config")
async def get_config():
    """获取当前配置"""
    # 重新加载配置以确保获取最新数据
    fetcher._load_config()
    return fetcher._config


@app.post("/api/config")
async def update_config(config: ConfigModel):
    """更新应用配置"""
    try:
        # 合并现有配置和新配置
        current_config = fetcher._config.copy()
        new_config = {**current_config, **config.dict(exclude_unset=True)}

        # 更新核心模块的配置并保存
        fetcher._config = new_config
        fetcher.save_config()
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/login")
async def login():
    """登录禅道系统获取令牌"""
    if not all([fetcher.zentao_url, fetcher.zentao_username, fetcher.zentao_password]):
        raise HTTPException(status_code=400, detail="Missing ZenTao credentials")

    token = await fetcher.get_zentao_token()
    if token:
        user_info = await fetcher.fetch_user_info()
        return {"status": "success", "token": token, "user_info": user_info}

    raise HTTPException(status_code=401, detail="Login failed")


@app.get("/api/products")
async def get_products():
    """获取产品列表"""
    if not fetcher.zentao_token:
        raise HTTPException(status_code=401, detail="Not logged in")

    products = await fetcher.fetch_products()
    return {"status": "success", "products": products}


@app.post("/api/select-product")
async def select_product(selection: ProductSelection):
    """选择当前操作的产品"""
    fetcher._config["selected_product_id"] = selection.product_id
    fetcher._config["selected_product"] = selection.product_name
    fetcher.save_config()
    return {
        "status": "success",
        "message": f"Product '{selection.product_name}' selected",
    }


@app.get("/api/bugs")
async def fetch_bugs():
    """获取当前用户未解决的Bug列表"""
    if not fetcher.zentao_token:
        raise HTTPException(status_code=401, detail="Not logged in")

    if not fetcher.selected_product_id:
        raise HTTPException(status_code=400, detail="No product selected")

    result = await fetcher.fetch_new_bugs()
    return result


@app.post("/api/send-to-feishu")
async def send_to_feishu(message: FeishuMessage):
    """发送消息到飞书"""
    if not fetcher.feishu_webhook_url:
        raise HTTPException(status_code=400, detail="Feishu webhook URL not configured")

    result = await fetcher.send_to_feishu(message)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@app.get("/api/status")
async def get_status():
    """获取当前应用状态"""
    return {
        "selected_product": fetcher.selected_product,
        "selected_product_id": fetcher.selected_product_id,
        "user_realname": fetcher.user_realname,
        "is_logged_in": bool(fetcher.zentao_token),
    }


@app.get("/api/refresh")
async def refresh_session():
    """刷新会话和用户信息"""
    if not fetcher.zentao_token:
        raise HTTPException(status_code=401, detail="Not logged in")

    # 刷新用户信息
    user_info = await fetcher.fetch_user_info()
    if user_info["status"] == "error":
        # 用户信息获取失败，可能是token过期
        token = await fetcher.get_zentao_token()
        if not token:
            raise HTTPException(status_code=401, detail="Session refresh failed")
        user_info = await fetcher.fetch_user_info()

    return {"status": "success", "user_info": user_info}
