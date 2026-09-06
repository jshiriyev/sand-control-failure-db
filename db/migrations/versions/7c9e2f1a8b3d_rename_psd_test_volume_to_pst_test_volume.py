"""rename completion_interval.psd_test_volume to pst_test_volume

Covers a small round of SME-feedback edits to MASTER.xlsx: the Parameter
"PSD Test Volume" was corrected to "PST Test Volume", which codegen
re-slugifies to the column name `pst_test_volume` (same Numeric type,
same OH Drilling Details subcategory). The other edits in this round --
"HES" -> "HEC" in the "Carrier Fluid Type - OHGP" dropdown, and a batch of
added / renamed options on the sand-control failure-mechanism dropdown --
are dropdown allow-list changes only. Those live in
`db/generated/field_registry.json` and are enforced at the API layer, not
by DB constraints (see CLAUDE.md "Schema"), so they need no migration.

No live Postgres was available to autogenerate against, so -- same as every
migration so far -- this is hand-authored. autogenerate would have emitted
this rename as drop_column + add_column; it is written here as an in-place
ALTER ... RENAME COLUMN so any existing values are preserved.

Revision ID: 7c9e2f1a8b3d
Revises: f04e20471f4a
Create Date: 2026-09-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7c9e2f1a8b3d'
down_revision: Union[str, Sequence[str], None] = 'f04e20471f4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "completion_interval",
        "psd_test_volume",
        new_column_name="pst_test_volume",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="PSD Test Volume",
        comment="PST Test Volume",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "completion_interval",
        "pst_test_volume",
        new_column_name="psd_test_volume",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="PST Test Volume",
        comment="PSD Test Volume",
    )
