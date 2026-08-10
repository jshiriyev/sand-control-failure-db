"""FastAPI application entrypoint.

    uvicorn backend.app.main:app --reload

(docker compose runs this via backend/docker-entrypoint.sh + backend/Dockerfile's CMD)
"""
from __future__ import annotations

from fastapi import FastAPI

from backend.app.config import get_settings
from backend.app.routers import health, records

settings = get_settings()

app = FastAPI(title=settings.api_title)
app.include_router(health.router)
app.include_router(records.router)
