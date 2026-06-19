from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VBANK_",
        extra="ignore",
    )

    app_name: str = "VBank"
    environment: Literal["local", "test", "production"] = "local"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "postgresql+psycopg://vbank_user:change_me@localhost:5432/vbank"
    database_echo: bool = False
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    access_token_secret: str = "change_me_for_local_development_secret"
    access_token_algorithm: str = "HS256"
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=365)
    refresh_token_transport: Literal["body", "cookie"] = "body"
    refresh_token_cookie_name: str = "vbank_refresh_token"
    refresh_token_cookie_secure: bool = False
    refresh_token_cookie_samesite: Literal["lax", "strict", "none"] = "lax"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
