"""SQLAlchemy engine/session factory. DATABASE_URL is read from the
environment on first use -- never hardcode credentials here.

Importing this module does not require DATABASE_URL to be set; only calling
get_engine()/get_db() does. That keeps `db.models`, `db.codegen`, etc.
importable in contexts (codegen, migration authoring, most tests) that never
touch a live connection.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        try:
            database_url = os.environ["DATABASE_URL"]
        except KeyError as exc:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy .env.example to .env and fill it in, "
                "or export DATABASE_URL directly."
            ) from exc
        _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a Session, always closed after the request."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
