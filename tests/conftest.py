"""Shared pytest fixtures.

Tests that need a real database read TEST_DATABASE_URL (falling back to
DATABASE_URL) from the environment and run real Alembic migrations against
it -- point it at the docker-compose Postgres (see README) or a GitHub
Actions service container. Tests that don't touch the database work with
neither variable set; DB-dependent fixtures skip cleanly instead of erroring
when no URL is configured.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve_test_database_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


def _alembic_config(url: str) -> Config:
    cfg = Config(str(REPO_ROOT / "db" / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def db_url() -> str:
    url = _resolve_test_database_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL (or DATABASE_URL) is not set -- skipping tests that need a real Postgres")
    return url


@pytest.fixture(scope="session")
def db_engine(db_url: str):
    cfg = _alembic_config(db_url)
    # Start from a known-empty schema so this fixture is safe to reuse
    # against a persistent local/dev database across repeated test runs.
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """A Session bound to one connection wrapped in an outer transaction
    that's always rolled back after the test, so tests never see each
    other's data. Application code (backend/app/services/record_ingest.py)
    calls session.commit() -- with join_transaction_mode="create_savepoint",
    SQLAlchemy 2.0 turns that into a SAVEPOINT release instead of actually
    ending the outer transaction, so the final rollback still undoes
    everything. See: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    """
    connection = db_engine.connect()
    outer_transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = session_factory()
    yield session
    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from backend.app.deps.db import get_db
    from backend.app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_payload():
    """Build a browser-valid API record for a chosen visibility branch.

    The registry decides which required fields apply after the controlling
    answers are set. This covers Onshore, No failure, and type-specific sand
    severity without copying those rules into the fixture.
    """
    from db.mapping import _BY_SCOPE, _applicable
    from dictionary import CURRENT_SCHEMA_VERSION

    def _sample(entry: dict, active_values: dict):
        kind = entry["kind"]
        if kind == "select":
            if entry.get("options_by"):
                trigger, choices = next(iter(entry["options_by"].items()))
                return choices[active_values[trigger]][0]
            return entry["options"][0]
        if kind == "date":
            return "2020-01-01"
        if kind == "number":
            return entry["min_value"] if entry["min_value"] is not None else 1
        if kind == "multi_number":
            return [1] * len(entry["db_columns"])
        if kind == "text" and entry["pattern"]:
            return "A" * max(entry["min_length"] or 1, 8)
        return "sample text"

    def _factory(sand_failure: str = "No", well_type: str = "Oil Producer",
                 environment: str = "Onshore") -> dict:
        buckets: dict[str, dict] = {scope: {} for scope in _BY_SCOPE}
        controls = {
            "Sand failure": sand_failure,
            "Well type": well_type,
            "Operating environment": environment,
        }
        for scope, index in _BY_SCOPE.items():
            bucket = buckets[scope]
            for entry in sorted(index.values(), key=lambda item: item["row_number"]):
                visible, active_values = _applicable(index, bucket)
                key = f"{entry['category']}::{entry['subcategory']}::{entry['parameter']}"
                if not visible[key] or not entry["required"]:
                    continue
                value = controls.get(entry["parameter"])
                if value is None:
                    value = _sample(entry, active_values)
                (bucket.setdefault(entry["category"], {})
                       .setdefault(entry["subcategory"], {})[entry["parameter"]]) = value
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "well": buckets.get("well", {}),
            "completion_intervals": [
                {"fields": buckets.get("completion_interval", {}),
                 "sand_bodies": [buckets.get("sand_body", {})]},
            ],
        }

    return _factory


@pytest.fixture()
def seeded_org(db_session):
    from backend.app.deps.auth import hash_token
    from db.models import Organization

    token = "test-token-12345"  # noqa: S105  (test fixture, not a real credential)
    org = Organization(name="Test Org", slug="test-org", api_token_hash=hash_token(token))
    db_session.add(org)
    db_session.flush()
    return org, token
