"""
Entry point for the arbitrage backend API.

This module configures the FastAPI application, including routes for
authentication, managing exchange keys and bot configuration, controlling
arbitrage bots and streaming real‑time updates via WebSocket. The API
expects clients to authenticate using JSON Web Tokens (JWT) returned
from the login endpoint.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta, datetime
from typing import List, Optional

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt

from .settings import get_settings
from . import models, schemas, crud
from .database import Base, engine, get_db
from .services.arbitrage import ArbitrageService

from sqlalchemy.ext.asyncio import AsyncSession


settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

arbitrage_service = ArbitrageService()


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise database and create tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_access_token(*, data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


@app.post("/auth/register", response_model=schemas.UserOut)
async def register_user(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)) -> models.User:
    existing = await crud.get_user_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await crud.create_user(db, user_in)
    return user


@app.post("/auth/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/exchange-keys", response_model=List[schemas.ExchangeKeyOut])
async def list_exchange_keys(
    current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await crud.get_exchange_keys(db, current_user.id)


@app.post("/exchange-keys", response_model=schemas.ExchangeKeyOut)
async def add_exchange_key(
    key_in: schemas.ExchangeKeyCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.create_exchange_key(db, current_user, key_in)


@app.post("/exchange-keys/{key_id}/enable", response_model=schemas.ExchangeKeyOut)
async def toggle_exchange_key(
    key_id: int,
    enabled: bool,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = await crud.set_exchange_key_enabled(db, key_id, enabled)
    if not key or key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Exchange key not found")
    return key


@app.get("/bot-configs", response_model=List[schemas.BotConfigOut])
async def list_bot_configs(
    current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await crud.get_bot_configs(db, current_user.id)


@app.post("/bot-configs", response_model=schemas.BotConfigOut)
async def add_bot_config(
    config_in: schemas.BotConfigCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.create_bot_config(db, current_user, config_in)


@app.put("/bot-configs/{config_id}", response_model=schemas.BotConfigOut)
async def update_bot_config(
    config_id: int,
    config_in: schemas.BotConfigCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await crud.update_bot_config(db, config_id, current_user.id, config_in)
    if not config:
        raise HTTPException(status_code=404, detail="Bot config not found")
    return config


@app.delete("/bot-configs/{config_id}")
async def delete_bot_config(
    config_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await crud.delete_bot_config(db, config_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot config not found")
    return {"detail": "deleted"}


@app.post("/bot-configs/{config_id}/start")
async def start_bot(
    config_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    configs = await crud.get_bot_configs(db, current_user.id)
    config = next((c for c in configs if c.id == config_id), None)
    if not config:
        raise HTTPException(status_code=404, detail="Bot config not found")
    await arbitrage_service.start_bot(current_user, config)
    return {"detail": "started"}


@app.post("/bot-configs/{config_id}/stop")
async def stop_bot(
    config_id: int,
    current_user: models.User = Depends(get_current_user),
):
    await arbitrage_service.stop_bot(current_user.id, config_id)
    return {"detail": "stopped"}


@app.get("/trade-logs", response_model=List[schemas.TradeLogOut])
async def get_trade_logs(
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs = await crud.get_trade_logs(db, current_user.id, limit=limit)
    return logs


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real‑time updates.

    Clients must pass a valid JWT via the `token` query parameter. Messages
    broadcast by the arbitrage service will be forwarded to the client.
    """
    # Authenticate token
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email = payload.get("sub")
        if email is None:
            raise JWTError()
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    # Accept connection
    await websocket.accept()
    # Resolve user
    async with get_db() as db:  # type: ignore[misc]
        user = await crud.get_user_by_email(db, email=email)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    user_id = user.id
    await arbitrage_service.subscribe(user_id, websocket)
    try:
        while True:
            # Keep connection alive by waiting for messages (if any). We don't
            # expect the client to send messages, but this will detect
            # disconnects.
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await arbitrage_service.unsubscribe(user_id, websocket)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(',')],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
