from typing import List, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.schemas import (
    NewsArticleResponse,
    NewsSummaryRequest,
    NewsSummaryResponse,
    PromptRequest,
    UpvoteResponse,
)
from api.security import get_current_user
from db.database import get_db_session
from models import NewsArticle, User
from services import NewsService, UpvoteService


router = APIRouter(prefix="/api/v1/news", tags=["news"])


@router.get("/news", response_model=List[NewsArticleResponse])
def get_all_news(db: Session = Depends(get_db_session)):
    service = NewsService(db)
    return service.get_all_news()


@router.get("/user_news", response_model=List[NewsArticleResponse])
def get_user_news_articles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    service = NewsService(db)
    user_id = cast(int, current_user.id)
    return service.get_user_news(user_id)


@router.post("/search_news")
def search_news(request: PromptRequest, db: Session = Depends(get_db_session)):
    """Search news by prompt (extract keywords using OpenAI)."""
    service = NewsService(db)
    # Implementation: extract keywords from prompt, then search
    # For now, this is a placeholder
    return {"message": "Search functionality to be implemented"}


@router.post("/news_summary", response_model=NewsSummaryResponse)
def summarize_news(
    request: NewsSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Generate summary for news content."""
    service = NewsService(db)
    summary_data = service._generate_summary([request.content])
    return summary_data


@router.post("/{article_id}/upvote", response_model=UpvoteResponse)
def upvote_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Toggle upvote on an article."""
    # Verify article exists
    article = db.query(NewsArticle).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    service = UpvoteService(db)
    user_id = cast(int, current_user.id)
    message = service.toggle_upvote(article_id, user_id)
    return {"message": message}
