"""sync well columns: sand failure mechanism follow-up edits

Covers this round of SME-feedback edits to MASTER.xlsx (see CLAUDE.md /
codegen output for the full context):

- New Parameter added at Well scope: "Did sanding start immediately after
  water breakthrough" (Yes/No dropdown) -> new `well.did_sanding_start_
  immediately_after_water_breakthrough` Text column.
- "Initial deviated well skin" -> "Initial Mechanical / Completion skin"
  and "Deviated well skin after choke-back" -> "Mechanical / Completion
  skin after choke-back": both a rename, same Numeric type, same
  subcategory -- done as in-place ALTER ... RENAME COLUMN so any existing
  values are preserved, not drop+add.
- The rest of this round's edits (dropdown option adds/removes on "Sand
  failure mechanism", and clearing `required` on a batch of Well Specific
  fields) are allow-list/validation-only changes enforced at the API layer
  via `db/generated/field_registry.json`, not by DB constraints (see
  CLAUDE.md "Schema"), so they need no migration.

No live Postgres was available to autogenerate against, so -- same as
every migration so far -- this is hand-authored: derived from a diff of
`db/generated/well_columns.py` before/after regenerating from the updated
MASTER.xlsx. autogenerate would have emitted the two renames as
drop_column + add_column; they're written here as ALTER COLUMN ... RENAME
COLUMN instead.

Revision ID: a686239533ca
Revises: 7c9e2f1a8b3d
Create Date: 2026-09-10 23:09:57.950789

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a686239533ca'
down_revision: Union[str, Sequence[str], None] = '7c9e2f1a8b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "well",
        sa.Column(
            "did_sanding_start_immediately_after_water_breakthrough",
            sa.Text(),
            nullable=True,
            comment="Did sanding start immediately after water breakthrough",
        ),
    )
    op.alter_column(
        "well",
        "initial_deviated_well_skin",
        new_column_name="initial_mechanical_completion_skin",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="Initial deviated well skin",
        comment="Initial Mechanical / Completion skin",
    )
    op.alter_column(
        "well",
        "deviated_well_skin_after_choke_back",
        new_column_name="mechanical_completion_skin_after_choke_back",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="Deviated well skin after choke-back",
        comment="Mechanical / Completion skin after choke-back",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "well",
        "mechanical_completion_skin_after_choke_back",
        new_column_name="deviated_well_skin_after_choke_back",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="Mechanical / Completion skin after choke-back",
        comment="Deviated well skin after choke-back",
    )
    op.alter_column(
        "well",
        "initial_mechanical_completion_skin",
        new_column_name="initial_deviated_well_skin",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="Initial Mechanical / Completion skin",
        comment="Initial deviated well skin",
    )
    op.drop_column("well", "did_sanding_start_immediately_after_water_breakthrough")
