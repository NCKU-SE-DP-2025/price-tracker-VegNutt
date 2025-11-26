import json
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
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _fetch_remote_news(self, search_term: str, is_initial: bool = False) -> List[dict]:
        all_news = []
        pages_range = range(1, settings.NEWS_FETCH_PAGES) if is_initial else range(1, 2)
        
        for page in pages_range:
            params = {
                "page": page,
                "id": f"search:{quote(search_term)}",
                "channelId": 2,
                "type": "searchword",
            }
            try:
                response = requests.get("https://udn.com/api/more", params=params, timeout=10)
                response.raise_for_status()
                all_news.extend(response.json().get("lists", []))
            except Exception as e:
                sentry_sdk.capture_exception(e)
                continue
        
        return all_news
    
    def _evaluate_relevance(self, title: str) -> str:
        """Use OpenAI to evaluate if news is relevant to price changes."""
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
            return content.strip() if content else "low"
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return "low"
    
    def _scrape_article_details(self, url: str) -> dict:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            title_el = soup.find("h1", class_="article-content__title")
            time_el = soup.find("time", class_="article-content__time")
            content_section = soup.find("section", class_="article-content__editor")
            
            title = title_el.text if title_el else "Unknown"
            time = time_el.text if time_el else ""
            
            paragraphs = []
            if content_section:
                for p in content_section.find_all("p"):
                    text = p.text.strip()
                    if text and "▪" not in text:
                        paragraphs.append(text)
            
            return {
                "title": title,
                "time": time,
                "content": paragraphs,
            }
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return {"title": "", "time": "", "content": []}
    
    def _generate_summary(self, content: List[str]) -> dict:
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
                return {"summary": "", "reason": ""}
            parsed = json.loads(result_text)
            return {
                "summary": parsed.get("影響", ""),
                "reason": parsed.get("原因", ""),
            }
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return {"summary": "", "reason": ""}
    
    def fetch_and_process_news(self, is_initial: bool = False) -> None:
        try:
            news_list = self._fetch_remote_news("價格", is_initial=is_initial)
            
            for news in news_list:
                title = news.get("title", "")
                url = news.get("titleLink", "")
                
                if not title or not url:
                    continue
                
                # Check if article already exists
                existing = self.db.query(NewsArticle).filter_by(url=url).first()
                if existing:
                    continue
                
                # Evaluate relevance
                relevance = self._evaluate_relevance(title)
                if relevance != "high":
                    continue
                
                # Scrape details
                details = self._scrape_article_details(url)
                if not details["content"]:
                    continue
                
                # Generate summary
                summary_data = self._generate_summary(details["content"])
                
                # Save to database
                article = NewsArticle(
                    url=url,
                    title=details["title"],
                    time=details["time"],
                    content=" ".join(details["content"]),
                    summary=summary_data["summary"],
                    reason=summary_data["reason"],
                )
                self.db.add(article)
                self.db.commit()
        
        except Exception as e:
            sentry_sdk.capture_exception(e)
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
