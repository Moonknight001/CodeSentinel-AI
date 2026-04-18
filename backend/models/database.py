"""
SQLAlchemy async database engine and session factory.

The connection URL is read from the ``DATABASE_URL`` environment variable.
Example:
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codesentinel
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def get_db_session() -> AsyncSession:
    """
    Async context manager that provides a database session.

    Use this outside of FastAPI's dependency injection system (e.g. in
    WebSocket handlers or background tasks) where ``Depends`` is not
    available::

        async with get_db_session() as db:
            await some_service(db, ...)
    """
    async with AsyncSessionLocal() as session:
        yield session
