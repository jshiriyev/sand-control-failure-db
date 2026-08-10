"""Application settings, read from environment variables (see .env.example).

Deliberately does NOT hold DATABASE_URL -- db/session.py owns that
independently, read lazily on first DB use, so importing this module (or
anything that imports it) never requires a database to be configured.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_title: str = "Sand Control Failure Database API"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
