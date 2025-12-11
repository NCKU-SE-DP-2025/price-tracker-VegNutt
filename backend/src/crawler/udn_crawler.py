"""UDN News Crawler implementation."""

import json
import logging
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import quote

from core.config import settings
from src.crawler.crawler_base import BaseCrawler
from src.crawler.exceptions import FetchException, ParseException, AnalysisException


logger = logging.getLogger(__name__)


class UDNCrawler(BaseCrawler):
    """Crawler for UDN (United Daily News) website.
    
    Fetches news articles from UDN's API and scrapes article details
    from their HTML pages.
    """
    
    API_URL = "https://udn.com/api/more"
    ARTICLE_BASE_URL = "https://udn.com"
    
    def __init__(self, timeout: int = 10, pages: int = 10):
        """Initialize UDN crawler.
        
        Args:
            timeout: HTTP request timeout in seconds
            pages: Number of pages to fetch (default: 10)
        """
        super().__init__(timeout)
        self.pages = pages
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch news from UDN API.
        
        Args:
            **kwargs: Supported parameters:
                - search_term (str): Search keyword (default: "價格" for prices)
                - is_initial (bool): Whether this is initial fetch (default: False)
            
        Returns:
            List of raw news items from API
            
        Raises:
            FetchException: If fetching fails
        """
        search_term = kwargs.get("search_term", "價格")
        is_initial = kwargs.get("is_initial", False)
        all_news = []
        pages_range = range(1, self.pages) if is_initial else range(1, 2)
        
        for page in pages_range:
            try:
                params = {
                    "page": page,
                    "id": f"search:{quote(search_term)}",
                    "channelId": 2,
                    "type": "searchword",
                }
                
                response = self.fetch_with_retry(self.API_URL, params=params)
                data = response.json()
                news_list = data.get("lists", [])
                all_news.extend(news_list)
                
                logger.debug(f"Fetched {len(news_list)} items from page {page}")
                
            except requests.RequestException as e:
                logger.error(f"Failed to fetch page {page}: {e}")
                raise FetchException(f"Failed to fetch UDN news page {page}: {str(e)}")
            except (ValueError, KeyError) as e:
                logger.error(f"Failed to parse API response: {e}")
                raise FetchException(f"Invalid API response format: {str(e)}")
        
        return all_news
    
    def parse_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single news item from API response.
        
        Args:
            item: Raw news item from API
            
        Returns:
            Standardized news item with title and URL
        """
        return {
            "title": item.get("title", ""),
            "url": item.get("titleLink", ""),
            "raw_data": item,
        }
    
    def scrape_article_details(self, url: str) -> Dict[str, Any]:
        """Scrape detailed article content from URL.
        
        Args:
            url: Article URL to scrape
            
        Returns:
            Dictionary with title, time, and content paragraphs
            
        Raises:
            ParseException: If scraping fails
        """
        try:
            response = self.fetch_with_retry(url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract article elements
            title_el = soup.find("h1", class_="article-content__title")
            time_el = soup.find("time", class_="article-content__time")
            content_section = soup.find("section", class_="article-content__editor")
            
            # Extract text
            title = title_el.text.strip() if title_el else "Unknown"
            time = time_el.text.strip() if time_el else ""
            
            # Extract paragraphs
            paragraphs = []
            if content_section:
                for p in content_section.find_all("p"):
                    text = p.text.strip()
                    # Filter out advertisement markers
                    if text and "▪" not in text:
                        paragraphs.append(text)
            
            logger.debug(f"Scraped article: {title}")
            
            return {
                "title": title,
                "time": time,
                "content": paragraphs,
            }
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch article {url}: {e}")
            raise ParseException(f"Failed to fetch article content: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse article {url}: {e}")
            raise ParseException(f"Failed to parse article content: {str(e)}")
    
    def validate_article(self, article: Dict[str, Any]) -> bool:
        """Validate if article has required fields.
        
        Args:
            article: Article dictionary to validate
            
        Returns:
            True if article is valid, False otherwise
        """
        return bool(
            article.get("title") and 
            article.get("url") and 
            article.get("content")
        )
    
    def evaluate_relevance(self, title: str) -> str:
        """Use OpenAI to evaluate if news is relevant to price changes.
        
        Args:
            title: Article title to evaluate
            
        Returns:
            Relevance score: 'high', 'medium', or 'low'
            
        Raises:
            AnalysisException: If evaluation fails
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)",
                },
                {"role": "user", "content": title},
            ]
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,  # type: ignore
                temperature=0.7,
            )
            content = response.choices[0].message.content
            result = content.strip() if content else "low"
            
            logger.debug(f"Evaluated relevance for '{title}': {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to evaluate relevance for '{title}': {e}")
            raise AnalysisException(f"Failed to evaluate article relevance: {str(e)}")
    
    def generate_summary(self, content: List[str]) -> Dict[str, str]:
        """Generate summary and reason using OpenAI.
        
        Args:
            content: List of article content paragraphs
            
        Returns:
            Dictionary with 'summary' and 'reason' keys
            
        Raises:
            AnalysisException: If summary generation fails
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
                },
                {"role": "user", "content": " ".join(content)},
            ]
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,  # type: ignore
                temperature=0.7,
            )
            result_text = response.choices[0].message.content
            
            if result_text is None:
                logger.warning("Empty response from OpenAI for summary generation")
                return {"summary": "", "reason": ""}
            
            parsed = json.loads(result_text)
            summary_data = {
                "summary": parsed.get("影響", ""),
                "reason": parsed.get("原因", ""),
            }
            
            logger.debug("Successfully generated summary and reason")
            return summary_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            raise AnalysisException(f"Invalid summary format from OpenAI: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise AnalysisException(f"Failed to generate news summary: {str(e)}")
