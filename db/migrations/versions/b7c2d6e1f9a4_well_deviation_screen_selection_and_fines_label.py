"""Replace interval length with deviation and update screen/fines fields.

Well Deviation is a different measurement from Completion Interval Length, so
it gets a new column. Screen Size Selection is a new optional dropdown. The
Fines Content edit changes only its label, so its column is renamed in place.

Revision ID: b7c2d6e1f9a4
Revises: a686239533ca
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2d6e1f9a4"
down_revision: Union[str, Sequence[str], None] = "a686239533ca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("completion_interval", "completion_interval_length")
    op.add_column(
        "completion_interval",
        sa.Column("well_deviation", sa.Numeric(), nullable=True, comment="Well Deviation"),
    )
    op.add_column(
        "completion_interval",
        sa.Column("screen_size_selection", sa.Text(), nullable=True, comment="Screen Size Selection"),
    )
    op.alter_column(
        "sand_body",
        "fines_content",
        new_column_name="fines_content_sub_44_microns",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="Fines Content",
        comment="Fines Content (Sub 44 microns)",
    )


def downgrade() -> None:
    op.alter_column(
        "sand_body",
        "fines_content_sub_44_microns",
        new_column_name="fines_content",
        existing_type=sa.Numeric(),
        existing_nullable=True,
        existing_comment="Fines Content (Sub 44 microns)",
        comment="Fines Content",
    )
    op.drop_column("completion_interval", "screen_size_selection")
    op.drop_column("completion_interval", "well_deviation")
    op.add_column(
        "completion_interval",
        sa.Column("completion_interval_length", sa.Numeric(), nullable=True, comment="Completion Interval Length"),
    )
