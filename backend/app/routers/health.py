"""Liveness check -- round-trips a real query so a broken DB connection
shows up here, not as a mysterious 500 on the first real request.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.deps.db import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
