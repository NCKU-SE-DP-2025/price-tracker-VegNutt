"""Database session management module.

Provides a centralized interface for database session creation and lifecycle
management, avoiding direct use of SessionLocal throughout the application.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from db.database import SessionLocal


logger = logging.getLogger(__name__)


class SessionManager:
    """Manages database session lifecycle.
    
    Provides a centralized interface for creating and managing database
    sessions with proper error handling and resource cleanup.
    """
    
    @staticmethod
    @contextmanager
    def get_session() -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.
        
        Usage:
            with SessionManager.get_session() as db:
                # Use db session
                result = db.query(Model).all()
        
        Yields:
            Session: SQLAlchemy database session
            
        Ensures:
            - Session is properly closed even if an exception occurs
            - Provides consistent session management across the application
        """
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()
    
    @staticmethod
    def create_session() -> Session:
        """Create a new database session without context manager.
        
        Use this only when you need direct control over session lifecycle.
        Prefer get_session() context manager in most cases.
        
        Returns:
            Session: SQLAlchemy database session
            
        Warning:
            Caller is responsible for closing the session via session.close()
        """
        return SessionLocal()
