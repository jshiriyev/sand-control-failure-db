"""Add separate weighting-agent and bridging-agent loading fields.

Both fields describe completion-interval drilling-fluid design. They are
optional nonnegative numeric inputs in lb/bbl; their range and unit labels are
defined in MASTER.xlsx and enforced by the generated form/API registry. The
database stores nullable Numeric values, matching the other dictionary-driven
columns.

Revision ID: c26f86a72b05
Revises: b7c2d6e1f9a4
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c26f86a72b05"
down_revision: Union[str, Sequence[str], None] = "b7c2d6e1f9a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "completion_interval",
        sa.Column("weighting_agent_loading", sa.Numeric(), nullable=True, comment="Weighting Agent Loading"),
    )
    op.add_column(
        "completion_interval",
        sa.Column("bridging_agent_loading", sa.Numeric(), nullable=True, comment="Bridging Agent Loading"),
    )


def downgrade() -> None:
    op.drop_column("completion_interval", "bridging_agent_loading")
    op.drop_column("completion_interval", "weighting_agent_loading")
