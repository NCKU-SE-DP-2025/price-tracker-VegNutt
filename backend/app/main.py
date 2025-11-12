from contextlib import asynccontextmanager

import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_news, routes_prices, routes_users
from app.core.config import settings
from app.db.database import Base, engine, SessionLocal
from app.services import NewsService
# Import models to register them with Base
from app.models import NewsArticle, User

sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)
Base.metadata.create_all(engine)
scheduler = BackgroundScheduler()


def start_scheduler():
    """Start background scheduler for periodic tasks."""
    try:
        db = SessionLocal()
        news_service = NewsService(db)
        
        # Fetch initial news if database is empty
        from app.models import NewsArticle
        if db.query(NewsArticle).count() == 0:
            news_service.fetch_and_process_news(is_initial=True)
        
        db.close()
    except Exception as e:
        sentry_sdk.capture_exception(e)
    
    # Schedule periodic news fetching
    scheduler.add_job(
        lambda: NewsService(SessionLocal()).fetch_and_process_news(),
        "interval",
        minutes=settings.NEWS_FETCH_INTERVAL_MINUTES,
    )
    scheduler.start()


def stop_scheduler():
    """Stop background scheduler."""
    if scheduler.running:
        scheduler.shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


# Create FastAPI application
app = FastAPI(
    title="Price Tracker API",
    description="API for tracking price-related news articles",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_users.router)
app.include_router(routes_news.router)  
app.include_router(routes_prices.router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
