"""initial schema

Creates the 4 baseline tables (organizations, well, production_interval,
completion_interval) exactly as defined by db/models/*.py, which in turn
build most of their columns from db/generated/*_columns.py (derived from
MASTER.xlsx by db/codegen.py).

This migration deliberately delegates to `Base.metadata.create_all()`
instead of the usual explicit `op.create_table(...)` calls Alembic
autogenerate would normally produce: it was authored without a live
Postgres available to diff against (see README's "Verification" notes), and
`create_all` guarantees byte-for-byte consistency with the ORM models by
construction rather than by careful hand-transcription of ~150 columns.
Every migration *after* this one should go back to the normal
`alembic revision --autogenerate` workflow against a real database.

As a sanity check once you have Postgres running: `alembic upgrade head`
followed by `alembic revision --autogenerate -m "check"` should produce an
EMPTY migration -- if it doesn't, this file and db/models/*.py have drifted
apart and the diff will tell you exactly how.

Revision ID: 5da737434937
Revises:
Create Date: 2026-08-09 21:32:24.811699

"""
import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import db.models  # noqa: E402,F401  (populates Base.metadata as a side effect)
from db.base import Base  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = '5da737434937'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Downgrade schema."""
    Base.metadata.drop_all(bind=op.get_bind())
