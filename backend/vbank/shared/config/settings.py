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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

