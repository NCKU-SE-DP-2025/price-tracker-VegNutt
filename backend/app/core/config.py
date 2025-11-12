import os
from typing import List


class Settings:
    """Application settings from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///news_database.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SENTRY_DSN: str = os.getenv(
        "SENTRY_DSN",
        "https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8080"]
    
    # News fetching
    NEWS_FETCH_INTERVAL_MINUTES: int = 100
    NEWS_FETCH_PAGES: int = 10


settings = Settings()
