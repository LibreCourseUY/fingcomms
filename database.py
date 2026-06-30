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
from sqlalchemy.orm import sessionmaker, DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from datetime import datetime
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "DEV")

_db_url = os.getenv("DATABASE_URL")
if ENVIRONMENT == "PROD":
    if not _db_url:
        raise RuntimeError("DATABASE_URL is required when ENVIRONMENT=PROD")
    _sync_db_url = _db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    DATABASE_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = _db_url if _db_url else "sqlite+aiosqlite:///./groups.db"
    _sync_db_url = DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///", 1)

try:
    from dbwarden import database_config as _old_db_config

    _old_db_config(
        database_name="primary",
        default=True,
        database_type="postgresql" if ENVIRONMENT == "PROD" else "sqlite",
        database_url_sync=_sync_db_url,
        dev_database_type="sqlite",
        dev_database_url="sqlite:///./groups.db",
        migrations_dir="migrations",
    )
except (ImportError, AttributeError):
    pass

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

_sync_engine = create_engine(_sync_db_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)


# ============================================================================
# DATABASE MODELS
# ============================================================================


class Base(DeclarativeBase):
    """
    Base class for all database models.
    SQLAlchemy will create tables for all classes that inherit from this.
    """

    pass


group_tags = Table(
    "group_tags",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


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
    tags = relationship("Tag", secondary=group_tags, lazy="selectin")


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


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now)


# ============================================================================
# DATABASE SESSION HELPER
# ============================================================================


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
