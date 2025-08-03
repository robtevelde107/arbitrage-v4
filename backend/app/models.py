"""
SQLAlchemy models defining the database schema for the arbitrage backend.

These models use SQLAlchemy's declarative mapping to create tables for
users, exchange API keys, bot configuration and trade logs. When adding
new tables or fields, be sure to run database migrations accordingly.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """User account model storing credentials and profile flags."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    exchange_keys: Mapped[list[ExchangeKey]] = relationship(
        "ExchangeKey", back_populates="user", cascade="all, delete-orphan"
    )
    bot_configs: Mapped[list[BotConfig]] = relationship(
        "BotConfig", back_populates="user", cascade="all, delete-orphan"
    )
    trade_logs: Mapped[list[TradeLog]] = relationship(
        "TradeLog", back_populates="user", cascade="all, delete-orphan"
    )


class ExchangeKey(Base):
    """API key and secret for a specific exchange and user."""

    __tablename__ = "exchange_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    exchange: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    api_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    api_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="exchange_keys")


class BotConfig(Base):
    """Configuration settings for arbitrage bot per user and mode."""

    __tablename__ = "bot_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), default="sandbox")  # sandbox or live
    coins: Mapped[str] = mapped_column(String(255), default="BTC,ETH")  # comma separated list
    budget: Mapped[float] = mapped_column(Float, default=0.0)
    max_trade_size: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_tolerance: Mapped[float] = mapped_column(Float, default=0.005)
    stop_loss: Mapped[float] = mapped_column(Float, default=0.1)  # percent of loss
    daily_limit: Mapped[float] = mapped_column(Float, default=0.2)  # daily loss limit (percentage)
    profit_take: Mapped[float] = mapped_column(Float, default=0.2)  # profit skim percentage
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="bot_configs")


class TradeLog(Base):
    """Detailed log of trades and actions taken by the bot."""

    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    coin: Mapped[str] = mapped_column(String(50))
    buy_exchange: Mapped[str] = mapped_column(String(50))
    sell_exchange: Mapped[str] = mapped_column(String(50))
    price_buy: Mapped[float] = mapped_column(Float)
    price_sell: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    profit: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(10))  # sandbox or live
    status: Mapped[str] = mapped_column(String(50), default="executed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="trade_logs")
