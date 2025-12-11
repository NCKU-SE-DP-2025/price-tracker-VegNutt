"""Base crawler class with common functionality."""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

import requests


logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base class for web crawlers.
    
    Provides common functionality for fetching, parsing, and analyzing
    web content from various sources.
    """
    
    def __init__(self, timeout: int = 10):
        """Initialize crawler with default settings.
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
    
    @abstractmethod
    def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data from source.
        
        Args:
            **kwargs: Source-specific parameters (e.g., search_term, is_initial, pages)
            
        Returns:
            List of dictionaries containing fetched data
        """
        pass
    
    @abstractmethod
    def parse_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single item from fetched data.
        
        Args:
            item: Raw data item to parse
            
        Returns:
            Parsed item with standardized fields
        """
        pass
    
    def fetch_with_retry(self, url: str, max_retries: int = 3, **kwargs) -> requests.Response:
        """Fetch URL with retry logic.
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for requests.get()
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                logger.debug(f"Successfully fetched {url} on attempt {attempt + 1}")
                return response
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise requests.RequestException(f"Failed to fetch {url} after {max_retries} attempts")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.session.close()
