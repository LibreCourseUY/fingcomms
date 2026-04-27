"""
Database Configuration and Models

This file defines the database schema using SQLAlchemy ORM (Object-Relational Mapping).
It creates the tables for storing groups and important links.

Key Concepts:
- SQLAlchemy: A Python library that provides database abstraction
- ORM: Maps Python classes to database tables
- SQLite: A simple file-based database (for development)
- The database URL can be changed via DATABASE_URL environment variable
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from datetime import datetime
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "DEV")

if ENVIRONMENT == "PROD":
    _db_url = os.getenv("DATABASE_URL")
    if not _db_url:
        raise RuntimeError("DATABASE_URL is required when ENVIRONMENT=PROD")
    DATABASE_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./groups.db")

from dbwarden import database_config

database_config(
    database_name="primary",
    default=True,
    database_type="postgresql" if ENVIRONMENT == "PROD" else "sqlite",
    database_url=DATABASE_URL,
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./groups.db",
)

if ENVIRONMENT == "PROD":
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
else:
    engine = create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


# ============================================================================
# DATABASE MODELS
# ============================================================================


class Base(DeclarativeBase):
    """
    Base class for all database models.
    SQLAlchemy will create tables for all classes that inherit from this.
    """

    pass


class Group(Base):
    """
    Model representing a student group or project.

    Fields:
    - id: Unique identifier (auto-incremented)
    - name: Group name (required)
    - description: Optional description of the group
    - url: Link to the group's website or repository
    - pinned: Whether this group appears at the top of listings
    - created_at: Timestamp when the group was added
    """

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    url = Column(String(500))
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class ImportantLink(Base):
    """
    Model representing important links for students.
    These are displayed on the frontend for quick access.

    Fields:
    - id: Unique identifier
    - title: Link title (required)
    - description: Optional description
    - url: The actual URL (required)
    - created_at: Timestamp when the link was added
    """

    __tablename__ = "important_links"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500))
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.now)


# ============================================================================
# DATABASE SESSION HELPER
# ============================================================================


def get_db():
    """
    FastAPI dependency that provides a database session for each request.

    Usage in FastAPI endpoints:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...

    The 'yield' provides the session, and the 'finally' block ensures
    it's always closed, even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
