from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from core.config import settings


# Database setup - Base must be created FIRST
Base = declarative_base()
engine = create_engine(settings.DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """Dependency: Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
