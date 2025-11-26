"""Background scheduler management module.

Encapsulates APScheduler lifecycle and job management to avoid global state
and improve testability and resource management.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler

from core.config import settings
from db.session import SessionManager
from services import NewsService


logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages background scheduler lifecycle and jobs.
    
    Encapsulates scheduler initialization, job scheduling, and shutdown.
    Provides a clean interface for startup/shutdown without global state.
    """
    
    _instance = None
    
    def __init__(self):
        """Initialize scheduler manager."""
        self._scheduler = BackgroundScheduler()
        self._is_running = False
    
    @classmethod
    def get_instance(cls):
        """Get or create singleton instance of SchedulerManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _fetch_and_process_news(self):
        """Dedicated method for periodic news fetching job.
        
        This method is called by the scheduler periodically. It handles
        database session creation and cleanup internally, avoiding lambda
        overhead and ensuring proper resource management.
        """
        try:
            with SessionManager.get_session() as db:
                news_service = NewsService(db)
                news_service.fetch_and_process_news()
                logger.debug("Periodic news fetch completed successfully")
        except Exception:
            logger.exception("Error during periodic news fetch")
    
    def start(self):
        """Start scheduler and schedule periodic tasks."""
        if self._is_running:
            logger.warning("Scheduler already running")
            return
        
        try:
            # Fetch initial news if database is empty
            with SessionManager.get_session() as db:
                from models import NewsArticle
                news_service = NewsService(db)
                if db.query(NewsArticle).count() == 0:
                    news_service.fetch_and_process_news(is_initial=True)
        except Exception:
            logger.exception("Error during initial news fetch")
        
        # Schedule periodic news fetching
        try:
            self._scheduler.add_job(
                self._fetch_and_process_news,
                "interval",
                minutes=settings.NEWS_FETCH_INTERVAL_MINUTES,
            )
            self._scheduler.start()
            self._is_running = True
            logger.info("Scheduler started successfully")
        except Exception:
            logger.exception("Failed to start scheduler")
    
    def stop(self):
        """Stop scheduler gracefully."""
        if not self._is_running:
            logger.warning("Scheduler not running")
            return
        
        try:
            if self._scheduler.running:
                self._scheduler.shutdown()
            self._is_running = False
            logger.info("Scheduler stopped successfully")
        except Exception:
            logger.exception("Error stopping scheduler")
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running
