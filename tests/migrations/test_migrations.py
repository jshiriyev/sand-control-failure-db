"""alembic upgrade head -> downgrade base -> upgrade head round-trips
cleanly against a real Postgres. Needs TEST_DATABASE_URL/DATABASE_URL (see
tests/conftest.py) -- skipped automatically when neither is set.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXPECTED_TABLES = {"organizations", "well", "completion_interval", "sand_body", "alembic_version"}


def test_upgrade_creates_all_tables(db_engine):
    tables = set(inspect(db_engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)


def test_downgrade_then_upgrade_round_trips(db_engine, db_url):
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(REPO_ROOT / "db" / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.downgrade(cfg, "base")
    assert "well" not in set(inspect(db_engine).get_table_names())

    command.upgrade(cfg, "head")
    assert "well" in set(inspect(db_engine).get_table_names())
