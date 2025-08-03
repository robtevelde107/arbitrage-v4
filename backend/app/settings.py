"""
Application configuration and settings management.

This module defines a Settings class that reads environment variables and
provides default values for running the arbitrage backend. It uses Pydantic's
BaseSettings for type casting and validation. If you deploy this on
PythonAnywhere or another hosting provider, be sure to set the appropriate
environment variables for sensitive data such as database URLs and secret keys.
"""

from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name: Human‑readable name for the API.
        api_v1_prefix: Prefix for versioned API routes.
        debug: Flag indicating debug mode.
        database_url: SQLAlchemy database URL.
        secret_key: Secret key used for JWT tokens and other security
            functionality.
        algorithm: Hashing algorithm for JWT.
        access_token_expire_minutes: JWT expiration time in minutes.
        allowed_origins: Comma separated list of allowed CORS origins.
    """

    app_name: str = Field(default="Arbitrage API", env="APP_NAME")
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    debug: bool = Field(default=False, env="DEBUG")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./arbitrage.db", env="DATABASE_URL"
    )
    secret_key: str = Field(default="change_me", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60 * 24, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    allowed_origins: str = Field(default="*", env="ALLOWED_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Using LRU cache ensures that environment variables are read only once
    during startup and the same Settings instance is reused throughout the
    application lifecycle.
    """

    return Settings()
