import unittest
from unittest.mock import patch, MagicMock
import os
import json
from bugfetcher.core import BugFetcherCore

class TestBugFetcherCore(unittest.TestCase):
    def setUp(self):
        self.config_path = "test_config.json"
        with open(self.config_path, "w") as f:
            json.dump({
                "zentao_url": "http://zentao.example.com",
                "zentao_username": "testuser",
                "zentao_password": "testpassword",
                "feishu_webhook_url": "http://feishu.example.com/webhook",
                "fetch_interval": 60,
                "selected_product_id": 1
            }, f)
        self.core = BugFetcherCore(self.config_path)

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

    def test_load_config(self):
        self.core._load_config()
        self.assertEqual(self.core.zentao_url, "http://zentao.example.com")
        self.assertEqual(self.core.zentao_username, "testuser")
        self.assertEqual(self.core.zentao_password, "testpassword")
        self.assertEqual(self.core.feishu_webhook_url, "http://feishu.example.com/webhook")
        self.assertEqual(self.core.fetch_interval, 60)
        self.assertEqual(self.core.selected_product_id, 1)

    @patch("aiohttp.ClientSession.post")
    async def test_get_zentao_token(self, mock_post):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = {"token": "testtoken"}
        mock_post.return_value.__aenter__.return_value = mock_response

        token = await self.core.get_zentao_token()
        self.assertEqual(token, "testtoken")

    @patch("aiohttp.ClientSession.get")
    async def test_fetch_user_info(self, mock_get):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = {"profile": {"realname": "Test User"}}
        mock_get.return_value.__aenter__.return_value = mock_response

        user_info = await self.core.fetch_user_info()
        self.assertEqual(user_info["status"], "success")
        self.assertEqual(user_info["realname"], "Test User")

    @patch("aiohttp.ClientSession.get")
    async def test_fetch_products(self, mock_get):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = {"products": [{"id": 1, "name": "Product 1"}]}
        mock_get.return_value.__aenter__.return_value = mock_response

        products = await self.core.fetch_products()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["id"], 1)
        self.assertEqual(products[0]["name"], "Product 1")

    @patch("aiohttp.ClientSession.get")
    async def test_fetch_new_bugs(self, mock_get):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "bugs": [
                {"id": 1, "title": "Bug 1", "assignedTo": {"realname": "Test User"}},
                {"id": 2, "title": "Bug 2", "assignedTo": {"realname": "Test User"}},
            ]
        }
        mock_get.return_value.__aenter__.return_value = mock_response

        bugs = await self.core.fetch_new_bugs()
        self.assertEqual(bugs["status"], "success")
        self.assertEqual(len(bugs["bugs"]), 2)

    @patch("aiohttp.ClientSession.post")
    async def test_send_to_feishu(self, mock_post):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response

        message = MagicMock()
        message.bugs = [
            {"id": 1, "title": "Bug 1"},
            {"id": 2, "title": "Bug 2"},
        ]
        message.total = 2
        message.realname = "Test User"
        message.suggestion = "Please fix these bugs."

        result = await self.core.send_to_feishu(message)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Message sent to Feishu")

if __name__ == "__main__":
    unittest.main()
