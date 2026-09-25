"""Use one sand-severity value and identify the developing record schema.

Oil and gas wells display different severity thresholds but a well record
stores only one selected severity. The other visible/required changes are
validation rules and need no SQL columns. Version 0 is intentionally mutable
until the first company records arrive; the explicit column makes each
submitted record's interpretation queryable alongside its raw JSON payload.

No company records exist yet, so the old mutually exclusive severity
columns can be replaced without a data backfill.

Revision ID: e41b59c2a7d3
Revises: c26f86a72b05
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e41b59c2a7d3"
down_revision: Union[str, Sequence[str], None] = "c26f86a72b05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("well", "severity_of_sand_production_gas_well")
    op.drop_column("well", "severity_of_sand_production_oil_well")
    op.add_column(
        "well",
        sa.Column("severity_of_sand_production", sa.Text(), nullable=True, comment="Severity of sand production"),
    )
    op.add_column("well", sa.Column("schema_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("well", "schema_version")
    op.drop_column("well", "severity_of_sand_production")
    op.add_column(
        "well",
        sa.Column(
            "severity_of_sand_production_oil_well", sa.Text(), nullable=True,
            comment="Severity of sand production - Oil Well",
        ),
    )
    op.add_column(
        "well",
        sa.Column(
            "severity_of_sand_production_gas_well", sa.Text(), nullable=True,
            comment="Severity of sand production - Gas Well",
        ),
    )
