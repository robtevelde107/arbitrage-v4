"""
Data access layer functions for interacting with the database.

These helper functions encapsulate common queries and modifications for
users, exchange keys, bot configs, and trade logs. Use them inside
service functions and route handlers to separate business logic from
persistence concerns.
"""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from passlib.context import CryptContext

from . import models, schemas

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def create_user(db: AsyncSession, user_in: schemas.UserCreate) -> models.User:
    """Create a new user in the database with a hashed password."""
    hashed_password = get_password_hash(user_in.password)
    user = models.User(email=user_in.email, hashed_password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    """Retrieve a user by their email address."""
    result = await db.execute(select(models.User).where(models.User.email == email))
    return result.scalar_one_or_none()


async def create_exchange_key(
    db: AsyncSession, user: models.User, key_in: schemas.ExchangeKeyCreate
) -> models.ExchangeKey:
    key = models.ExchangeKey(
        user_id=user.id,
        exchange=key_in.exchange,
        api_key=key_in.api_key,
        api_secret=key_in.api_secret,
        api_password=key_in.api_password,
        is_enabled=key_in.is_enabled,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


async def get_exchange_keys(db: AsyncSession, user_id: int) -> list[models.ExchangeKey]:
    result = await db.execute(
        select(models.ExchangeKey).where(models.ExchangeKey.user_id == user_id)
    )
    return list(result.scalars().all())


async def set_exchange_key_enabled(
    db: AsyncSession, key_id: int, enabled: bool
) -> Optional[models.ExchangeKey]:
    result = await db.execute(
        select(models.ExchangeKey).where(models.ExchangeKey.id == key_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return None
    key.is_enabled = enabled
    await db.commit()
    await db.refresh(key)
    return key


async def create_bot_config(
    db: AsyncSession, user: models.User, config_in: schemas.BotConfigCreate
) -> models.BotConfig:
    config = models.BotConfig(
        user_id=user.id,
        mode=config_in.mode,
        coins=config_in.coins,
        budget=config_in.budget,
        max_trade_size=config_in.max_trade_size,
        slippage_tolerance=config_in.slippage_tolerance,
        stop_loss=config_in.stop_loss,
        daily_limit=config_in.daily_limit,
        profit_take=config_in.profit_take,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


async def get_bot_configs(db: AsyncSession, user_id: int) -> list[models.BotConfig]:
    result = await db.execute(
        select(models.BotConfig).where(models.BotConfig.user_id == user_id)
    )
    return list(result.scalars().all())


async def update_bot_config(
    db: AsyncSession,
    config_id: int,
    user_id: int,
    config_in: schemas.BotConfigCreate,
) -> Optional[models.BotConfig]:
    result = await db.execute(
        select(models.BotConfig).where(
            models.BotConfig.id == config_id, models.BotConfig.user_id == user_id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return None
    for field, value in config_in.model_dump().items():
        setattr(config, field, value)
    await db.commit()
    await db.refresh(config)
    return config


async def delete_bot_config(db: AsyncSession, config_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(models.BotConfig).where(
            models.BotConfig.id == config_id, models.BotConfig.user_id == user_id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return False
    await db.delete(config)
    await db.commit()
    return True


async def create_trade_log(
    db: AsyncSession,
    user_id: int,
    coin: str,
    buy_exchange: str,
    sell_exchange: str,
    price_buy: float,
    price_sell: float,
    amount: float,
    profit: float,
    mode: str,
    status: str,
    error_message: Optional[str] = None,
) -> models.TradeLog:
    log = models.TradeLog(
        user_id=user_id,
        coin=coin,
        buy_exchange=buy_exchange,
        sell_exchange=sell_exchange,
        price_buy=price_buy,
        price_sell=price_sell,
        amount=amount,
        profit=profit,
        mode=mode,
        status=status,
        error_message=error_message,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_trade_logs(db: AsyncSession, user_id: int, limit: int = 100) -> list[models.TradeLog]:
    result = await db.execute(
        select(models.TradeLog)
        .where(models.TradeLog.user_id == user_id)
        .order_by(models.TradeLog.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
