"""Creates a couple of dev-only organizations with known API tokens, for
local development and manual API testing. Idempotent by slug -- safe to run
repeatedly. Only intended for the local/dev database started by docker
compose; never point this at anything containing real data (the plaintext
tokens are printed to stdout, and dev orgs are not something you want in a
production system).

    python -m db.seed.dev_organizations
"""
from __future__ import annotations

import hashlib
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from db.models import Organization  # noqa: E402
from db.session import get_sessionmaker  # noqa: E402

DEV_ORG_SLUGS = ["dev-operator", "dev-service-co"]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def seed() -> None:
    session = get_sessionmaker()()
    try:
        for slug in DEV_ORG_SLUGS:
            existing = session.query(Organization).filter_by(slug=slug).first()
            if existing is not None:
                print(f"organization {slug!r} already exists (id={existing.id}), skipping")
                continue
            token = secrets.token_urlsafe(32)
            org = Organization(name=slug.replace("-", " ").title(), slug=slug, api_token_hash=hash_token(token))
            session.add(org)
            session.flush()
            print(f"created organization {slug!r} (id={org.id}) -- token: {token}")
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
