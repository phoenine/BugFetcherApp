import argparse
import asyncio
from ..core import BugFetcherCore

async def run_cli(args):
    parser = argparse.ArgumentParser(description="ZenTao Bug Fetcher CLI")
    # parser.add_argument("--url", help="ZenTao URL")
    parser.add_argument("--username", help="ZenTao username")
    parser.add_argument("--password", help="ZenTao password")
    # parser.add_argument("--feishu", help="Feishu Webhook URL")
    parser.add_argument("--product", help="Product id")
    parser.add_argument("--interval", type=int, default=60, help="Fetch interval in minutes")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args(args)

    fetcher = BugFetcherCore()
    if args.username:
        fetcher._config["zentao_username"] = args.username
    if args.password:
        fetcher._config["zentao_password"] = args.password
    if args.product:
        fetcher._config["selected_product_id"] = args.product
    fetcher.save_config()
    fetcher._load_config()
    fetcher.zentao_token = ""

    # 统一登录凭证校验
    if not all([fetcher.zentao_url, fetcher.zentao_username, fetcher.zentao_password]):
        fetcher.log_message("Missing credentials - need url, username and password")
        raise ValueError("Missing credentials - need url, username and password")

    if not fetcher.zentao_token:
        fetcher.log_message("Getting ZenTao token")
        fetcher.zentao_token = await fetcher.get_zentao_token()
        fetcher.save_config()  # 保持与API相同的保存逻辑

    fetcher.log_message("Fetching user info")
    user_info = await fetcher.fetch_user_info()
    if user_info["status"] == "error":
        fetcher.log_message(f"Failed to fetch user info: {user_info['message']}")
        return

    if not fetcher.selected_product_id:
        fetcher.log_message("Fetching products")
        products = await fetcher.fetch_products()
        if products:
            print("Available products:")
            for i, p in enumerate(products):
                print(f"{i+1}. {p['name']}")
            choice = int(input("Select product number: ")) - 1
            # 使用与API相同的产品选择保存方式
            fetcher.log_message(f"Selected product: {products[choice]['name']}")
            fetcher.update_config({
                "selected_product": products[choice]['name'],
                "selected_product_id": products[choice]['id']
            })

    if args.once:
        fetcher.log_message("Fetching new bugs")
        bugs = await fetcher.fetch_new_bugs()
        if bugs["status"] == "error":
            fetcher.log_message(f"Failed to fetch new bugs: {bugs['message']}")
        else:
            fetcher.log_message(f"Total new bugs: {len(bugs['bugs'])}")
    else:
        import time
        while True:
            fetcher.log_message("Fetching new bugs")
            bugs = await fetcher.fetch_new_bugs()
            if bugs["status"] == "error":
                fetcher.log_message(f"Failed to fetch new bugs: {bugs['message']}")
            else:
                fetcher.log_message(f"Total new bugs: {len(bugs['bugs'])}")
            print(f"Next fetch in {args.interval} minutes")
            await asyncio.sleep(args.interval * 60)

if __name__ == "__main__":
    import sys
    asyncio.run(run_cli(sys.argv[1:]))
