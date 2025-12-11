import unittest
from unittest.mock import patch, MagicMock
import requests
from src.crawler.crawler_base import BaseCrawler

class ConcreteCrawler(BaseCrawler):
    def fetch_data(self, **kwargs):
        return []
    
    def parse_item(self, item):
        return {}

class TestBaseCrawler(unittest.TestCase):

    def setUp(self):
        self.crawler = ConcreteCrawler(timeout=5)

    def tearDown(self):
        if self.crawler.session:
            self.crawler.session.close()

    @patch('requests.Session.get')
    def test_fetch_with_retry_success(self, mock_get):
        """測試重試機制：第一次就成功"""
        # 模擬 Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        response = self.crawler.fetch_with_retry("http://example.com")
        
        self.assertEqual(response, mock_response)
        mock_get.assert_called_once() # 確認只呼叫了一次

    @patch('requests.Session.get')
    def test_fetch_with_retry_logic(self, mock_get):
        """測試重試機制：失敗兩次，第三次成功"""
        success_response = MagicMock()
        success_response.status_code = 200
        
        mock_get.side_effect = [
            requests.ConnectionError("Fail 1"),
            requests.ConnectionError("Fail 2"),
            success_response
        ]

        response = self.crawler.fetch_with_retry("http://example.com", max_retries=3)
        
        self.assertEqual(response, success_response)
        self.assertEqual(mock_get.call_count, 3) # 確認呼叫了三次

    @patch('requests.Session.get')
    def test_fetch_with_retry_failure(self, mock_get):
        """測試重試機制：全部失敗，應拋出異常"""
        mock_get.side_effect = requests.ConnectionError("Always fail")

        with self.assertRaises(requests.RequestException):
            self.crawler.fetch_with_retry("http://example.com", max_retries=3)
        
        self.assertEqual(mock_get.call_count, 3)

    def test_context_manager(self):
        """測試 with 語法是否正確關閉 session"""
        with ConcreteCrawler() as crawler:
            self.assertIsInstance(crawler, BaseCrawler)