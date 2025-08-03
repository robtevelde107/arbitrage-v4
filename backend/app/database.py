"""
Database utilities for the arbitrage backend.

This module configures the SQLAlchemy async engine and session maker. It
uses the database URL specified in the application settings. By default
the application uses an in‑process SQLite database, but you should set
DATABASE_URL to a PostgreSQL or other persistent database when running in
production. To avoid blocking the event loop, only async database APIs are
used throughout the application.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .settings import get_settings


settings = get_settings()

# SQLAlchemy declarative base.
#
# We expose a `Base` object so that models can inherit from it and
# register themselves with SQLAlchemy's metadata.  Without this,
# attempts to import `Base` from `app.database` in other modules would
# fail on Python 3.9, causing runtime errors during app startup.
Base = declarative_base()

# Create the async engine. The pool_pre_ping flag ensures connections are
# validated prior to use, preventing stale connections from raising errors.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
)

# Configure the sessionmaker for asynchronous operation.
async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    """Provide a transactional scope for database operations.

    This function can be used as a FastAPI dependency. It yields an
    AsyncSession instance and ensures that the session is closed after the
    request lifecycle finishes. Committing transactions is left to the
    caller to control when necessary.
    """
    async with async_session_factory() as session:  # type: AsyncSession
        try:
            yield session
        finally:
            await session.close()
