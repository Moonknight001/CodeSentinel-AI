"""
SQLAlchemy async database engine and session factory.

The connection URL is read from the ``DATABASE_URL`` environment variable.
Example:
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codesentinel
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/codesentinel",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields an async database session and guarantees
    the session is closed after the request.
    """
    async with AsyncSessionLocal() as session:
        yield session
