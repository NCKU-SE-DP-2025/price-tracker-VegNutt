"""
UDN Crawler Usage Examples

This document shows how to use the refactored UDN crawler module.
"""

# Example 1: Basic usage - Fetch news
from src.crawler import UDNCrawler

crawler = UDNCrawler(timeout=10, pages=10)
news_items = crawler.fetch_data(search_term="價格", is_initial=True)

for raw_item in news_items:
    parsed_item = crawler.parse_item(raw_item)
    print(f"Title: {parsed_item['title']}")
    print(f"URL: {parsed_item['url']}")


# Example 2: Using context manager (recommended)
with UDNCrawler(timeout=10, pages=10) as crawler:
    news_items = crawler.fetch_data(search_term="價格")
    
    for raw_item in news_items:
        parsed = crawler.parse_item(raw_item)
        
        try:
            details = crawler.scrape_article_details(parsed['url'])
            print(f"Title: {details['title']}")
            print(f"Time: {details['time']}")
            print(f"Content paragraphs: {len(details['content'])}")
        except Exception as e:
            print(f"Failed to scrape {parsed['url']}: {e}")


# Example 3: Validation before processing
with UDNCrawler() as crawler:
    news_items = crawler.fetch_data()
    
    for raw_item in news_items:
        parsed = crawler.parse_item(raw_item)
        
        # Validate before scraping
        if not parsed['title'] or not parsed['url']:
            continue
        
        try:
            details = crawler.scrape_article_details(parsed['url'])
            
            # Validate scraped content
            if crawler.validate_article(details):
                print(f"Valid article: {details['title']}")
            else:
                print(f"Invalid article (missing content): {details['title']}")
        
        except Exception as e:
            print(f"Error processing {parsed['url']}: {e}")


# Example 4: Integration with NewsService (next step)
"""
The refactored NewsService would look like:

class NewsService:
    def __init__(self, db: Session):
        self.db = db
        self.crawler = UDNCrawler()
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def fetch_and_process_news(self, is_initial: bool = False) -> None:
        with self.crawler:
            news_items = self.crawler.fetch_data(is_initial=is_initial)
            
            for raw_item in news_items:
                parsed = self.crawler.parse_item(raw_item)
                
                # Check if article already exists
                if self.db.query(NewsArticle).filter_by(url=parsed['url']).first():
                    continue
                
                # Scrape article details
                try:
                    details = self.crawler.scrape_article_details(parsed['url'])
                except Exception as e:
                    logger.error(f"Failed to scrape {parsed['url']}: {e}")
                    continue
                
                # Evaluate relevance (AI)
                relevance = self._evaluate_relevance(details['title'])
                if relevance != "high":
                    continue
                
                # Generate summary (AI)
                summary_data = self._generate_summary(details['content'])
                
                # Save to database
                article = NewsArticle(
                    url=parsed['url'],
                    title=details['title'],
                    time=details['time'],
                    content=" ".join(details['content']),
                    summary=summary_data["summary"],
                    reason=summary_data["reason"],
                )
                self.db.add(article)
                self.db.commit()
"""
