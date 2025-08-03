"""
Pydantic schemas for request and response payloads.

These schemas define the shape of the data exchanged via the API. They
validate input data and control what fields are exposed in responses. When
adding new fields or models, remember to update the corresponding schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

# Pydantic imports
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserOut(UserBase):
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        # Pydantic v2: use from_attributes instead of orm_mode
        from_attributes = True


class ExchangeKeyBase(BaseModel):
    exchange: str
    api_key: str
    api_secret: str
    api_password: Optional[str] = None
    is_enabled: bool = False


class ExchangeKeyCreate(ExchangeKeyBase):
    pass


class ExchangeKeyOut(ExchangeKeyBase):
    id: int
    user_id: int

    class Config:
        # Pydantic v2: use from_attributes instead of orm_mode
        from_attributes = True


class BotConfigBase(BaseModel):
    # Use pattern instead of deprecated regex for Pydantic v2 compatibility
    mode: str = Field(default="sandbox", pattern=r"^(sandbox|live)$")  # sandbox or live
    coins: str = Field(default="BTC,ETH")  # comma separated list
    budget: float = 0.0
    max_trade_size: float = 0.0
    slippage_tolerance: float = 0.005
    stop_loss: float = 0.1
    daily_limit: float = 0.2
    profit_take: float = 0.2


class BotConfigCreate(BotConfigBase):
    pass


class BotConfigOut(BotConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        # Pydantic v2: use from_attributes instead of orm_mode
        from_attributes = True


class TradeLogOut(BaseModel):
    id: int
    user_id: int
    timestamp: datetime
    coin: str
    buy_exchange: str
    sell_exchange: str
    price_buy: float
    price_sell: float
    amount: float
    profit: float
    mode: str
    status: str
    error_message: Optional[str] = None

    class Config:
        # Pydantic v2: use from_attributes instead of orm_mode
        from_attributes = True


class ApiKeyOut(BaseModel):
    message: str
