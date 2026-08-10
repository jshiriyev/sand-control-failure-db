"""FastAPI's DB-session dependency -- a thin, separately-overridable
indirection point over db.session.get_db (tests override this exact name via
`app.dependency_overrides[get_db]` to inject a per-test rollback session).
"""
from __future__ import annotations

from db.session import get_db

__all__ = ["get_db"]
