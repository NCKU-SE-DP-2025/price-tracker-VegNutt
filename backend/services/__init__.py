import json
import logging
from typing import List, Optional, cast

import requests
import sentry_sdk
from bs4 import BeautifulSoup
from openai import OpenAI
from sqlalchemy import delete, insert, select, func
from sqlalchemy.orm import Session
from urllib.parse import quote

from core.config import settings
from models import NewsArticle, User, user_news_association_table
from api.security import hash_password, verify_password
from src.crawler.udn_crawler import UDNCrawler
from src.crawler.exceptions import CrawlerException, AnalysisException


logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, cast(str, user.hashed_password)):
            return None
        return user
    
    @staticmethod
    def create_user(db: Session, username: str, password: str) -> User:
        hashed_pwd = hash_password(password)
        user = User(username=username, hashed_password=hashed_pwd)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


class NewsService:
    def __init__(self, db: Session):
        self.db = db
    
    def fetch_and_process_news(self, is_initial: bool = False) -> None:
        """Fetch and process news from UDN using the crawler.
        
        Uses UDNCrawler to fetch articles and process them through
        relevance evaluation and summary generation pipeline.
        """
        try:
            crawler = UDNCrawler()
            
            # Fetch articles from UDN
            all_news = crawler.fetch_data(search_term="價格", is_initial=is_initial)
            
            for news in all_news:
                title = news.get("title", "")
                url = news.get("titleLink", "")
                
                if not title or not url:
                    continue
                
                # Check if article already exists
                existing = self.db.query(NewsArticle).filter_by(url=url).first()
                if existing:
                    continue
                
                # Evaluate relevance using crawler
                try:
                    relevance = crawler.evaluate_relevance(title)
                except AnalysisException as e:
                    logger.error(f"Failed to evaluate relevance: {e}")
                    continue
                
                if relevance != "high":
                    continue
                
                # Scrape article details using crawler
                try:
                    details = crawler.scrape_article_details(url)
                except CrawlerException as e:
                    logger.error(f"Failed to scrape article details: {e}")
                    continue
                
                if not details.get("content"):
                    continue
                
                # Generate summary using crawler
                try:
                    summary_data = crawler.generate_summary(details.get("content", []))
                except AnalysisException as e:
                    logger.error(f"Failed to generate summary: {e}")
                    summary_data = {"summary": "", "reason": ""}
                
                # Save to database
                article = NewsArticle(
                    url=url,
                    title=details.get("title", ""),
                    time=details.get("time", ""),
                    content=" ".join(details.get("content", [])),
                    summary=summary_data.get("summary", ""),
                    reason=summary_data.get("reason", ""),
                )
                self.db.add(article)
                self.db.commit()
        
        except CrawlerException as e:
            logger.error(f"Crawler error during news processing: {e}")
            self.db.rollback()
        except Exception as e:
            logger.exception(f"Unexpected error during news processing: {e}")
            self.db.rollback()
    
    def get_all_news(self) -> List[dict]:
        """Get all news articles with upvote counts.
        
        Optimized to use single aggregated query instead of N+1 queries.
        Uses LEFT OUTER JOIN to count upvotes without looping through articles.
        """
        # Single optimized query with aggregation
        query = self.db.query(
            NewsArticle,
            func.count(user_news_association_table.c.user_id).label("upvote_count")
        ).outerjoin(
            user_news_association_table,
            NewsArticle.id == user_news_association_table.c.news_articles_id
        ).group_by(
            NewsArticle.id
        ).order_by(
            NewsArticle.time.desc()
        )
        
        result = []
        for article, upvote_count in query.all():
            result.append({
                "id": article.id,
                "url": article.url,
                "title": article.title,
                "time": article.time,
                "content": article.content,
                "summary": article.summary,
                "reason": article.reason,
                "upvotes": upvote_count or 0,
                "is_upvoted": False,
            })
        return result
    
    def get_user_news(self, user_id: int) -> List[dict]:
        """Get all news with upvote status for specific user.
        
        Optimized to use 2 queries instead of N+2 queries:
        1. Get all articles with upvote counts (single aggregated query)
        2. Get upvoted article IDs by user (single subquery)
        """
        # Query 1: Get all articles with upvote counts
        articles_query = self.db.query(
            NewsArticle,
            func.count(user_news_association_table.c.user_id).label("upvote_count")
        ).outerjoin(
            user_news_association_table,
            NewsArticle.id == user_news_association_table.c.news_articles_id
        ).group_by(
            NewsArticle.id
        ).order_by(
            NewsArticle.time.desc()
        )
        
        # Query 2: Get set of article IDs upvoted by this user (for fast lookup)
        upvoted_ids = set(
            self.db.query(user_news_association_table.c.news_articles_id).filter_by(
                user_id=user_id
            ).all()
        )
        upvoted_ids = {row[0] for row in upvoted_ids}  # Convert tuples to set of IDs
        
        result = []
        for article, upvote_count in articles_query.all():
            result.append({
                "id": article.id,
                "url": article.url,
                "title": article.title,
                "time": article.time,
                "content": article.content,
                "summary": article.summary,
                "reason": article.reason,
                "upvotes": upvote_count or 0,
                "is_upvoted": article.id in upvoted_ids,
            })
        return result


class UpvoteService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def toggle_upvote(self, article_id: int, user_id: int) -> str:
        """Toggle upvote for an article by a user."""
        existing = self.db.execute(
            select(user_news_association_table).where(
                user_news_association_table.c.news_articles_id == article_id,
                user_news_association_table.c.user_id == user_id,
            )
        ).scalar()
        
        if existing:
            self.db.execute(
                delete(user_news_association_table).where(
                    user_news_association_table.c.news_articles_id == article_id,
                    user_news_association_table.c.user_id == user_id,
                )
            )
            message = "Upvote removed"
        else:
            self.db.execute(
                insert(user_news_association_table).values(
                    news_articles_id=article_id,
                    user_id=user_id,
                )
            )
            message = "Article upvoted"
        
        self.db.commit()
        return message
