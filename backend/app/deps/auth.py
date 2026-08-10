"""Org-token bearer authentication.

Each organization has one shared API token; requests authenticate with
`Authorization: Bearer <token>`. Only the token's SHA-256 hash is ever
stored (organizations.api_token_hash) -- the plaintext is shown to the org
exactly once, at creation time.
"""
from __future__ import annotations

import hashlib

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.deps.db import get_db
from db.models import Organization


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_current_org(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Organization:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header (expected 'Bearer <token>')",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    org = db.query(Organization).filter_by(api_token_hash=hash_token(token), is_active=True).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return org
