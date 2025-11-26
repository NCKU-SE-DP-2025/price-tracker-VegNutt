"""UDN News Crawler implementation."""

import logging
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

from core.config import settings
from src.crawler.crawler_base import BaseCrawler
from src.crawler.exceptions import FetchException, ParseException


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
