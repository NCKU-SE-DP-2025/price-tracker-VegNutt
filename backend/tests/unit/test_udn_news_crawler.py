import unittest
from unittest.mock import patch, MagicMock
from src.crawler.udn_crawler import UDNCrawler
from src.crawler.exceptions import FetchException, ParseException

class TestUDNCrawler(unittest.TestCase):

    def setUp(self):
        self.crawler = UDNCrawler(timeout=5, pages=1)

    # --- 測試 fetch_data (API 部分) ---

    @patch('src.crawler.udn_crawler.UDNCrawler.fetch_with_retry')
    def test_fetch_data_success(self, mock_fetch):
        """測試成功從 API 獲取新聞列表"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lists": [
                {"title": "News 1", "titleLink": "http://udn.com/1"},
                {"title": "News 2", "titleLink": "http://udn.com/2"}
            ]
        }
        mock_fetch.return_value = mock_response

        results = self.crawler.fetch_data(search_term="test", is_initial=False)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], "News 1")
        # 確認有呼叫正確的 API URL
        mock_fetch.assert_called()
        args, kwargs = mock_fetch.call_args
        self.assertEqual(args[0], self.crawler.API_URL)

    @patch('src.crawler.udn_crawler.UDNCrawler.fetch_with_retry')
    def test_fetch_data_api_error(self, mock_fetch):
        """測試 API 回傳格式錯誤或請求失敗"""
        # 模擬 fetch 失敗
        import requests
        mock_fetch.side_effect = requests.RequestException("API Error")

        with self.assertRaises(FetchException):
            self.crawler.fetch_data()

    # --- 測試 parse_item (單項資料標準化) ---

    def test_parse_item(self):
        """測試將 API 的原始資料轉換為標準格式"""
        raw_item = {
            "title": "Test Title",
            "titleLink": "http://udn.com/test",
            "other_field": "ignore me"
        }
        parsed = self.crawler.parse_item(raw_item)
        
        self.assertEqual(parsed['title'], "Test Title")
        self.assertEqual(parsed['url'], "http://udn.com/test")
        self.assertEqual(parsed['raw_data'], raw_item)

    # --- 測試 scrape_article_details (HTML 解析) ---

    @patch('src.crawler.udn_crawler.UDNCrawler.fetch_with_retry')
    def test_scrape_article_details_success(self, mock_fetch):
        """測試解析新聞內文 HTML"""
        html_content = """
        <html>
            <body>
                <h1 class="article-content__title">  Test Headline  </h1>
                <time class="article-content__time"> 2024-01-01 10:00 </time>
                <section class="article-content__editor">
                    <p>Paragraph 1</p>
                    <p>Paragraph 2</p>
                    <p>Advertisement ▪ ignored</p>
                </section>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        mock_fetch.return_value = mock_response

        result = self.crawler.scrape_article_details("http://udn.com/news/123")

        self.assertEqual(result['title'], "Test Headline")
        self.assertEqual(result['time'], "2024-01-01 10:00")
        self.assertEqual(len(result['content']), 2) 
        self.assertEqual(result['content'][0], "Paragraph 1")

    @patch('src.crawler.udn_crawler.UDNCrawler.fetch_with_retry')
    def test_scrape_article_details_failure(self, mock_fetch):
        """測試解析失敗的情況"""
        import requests
        mock_fetch.side_effect = requests.RequestException("404 Not Found")

        with self.assertRaises(ParseException):
            self.crawler.scrape_article_details("http://udn.com/bad-url")

    # --- 測試 validate_article ---

    def test_validate_article(self):
        """測試文章欄位驗證"""
        valid_article = {
            "title": "Title",
            "url": "http://url",
            "content": ["text"]
        }
        invalid_article = {
            "title": "", # 標題為空
            "url": "http://url",
            "content": []
        }
        
        self.assertTrue(self.crawler.validate_article(valid_article))
        self.assertFalse(self.crawler.validate_article(invalid_article))

if __name__ == "__main__":
    unittest.main()