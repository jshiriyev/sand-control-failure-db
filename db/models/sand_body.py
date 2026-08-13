"""The `sand_body` table -- one row per Sand Body within a completion
interval, plus the dictionary-driven columns generated from MASTER.xlsx's
Sand-Body-scope parameters (see db/generated/sand_body_columns.py, never
hand-edited).
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, UniqueConstraint, func
from sqlalchemy.orm import relationship

from db.base import Base
from db.generated.sand_body_columns import SAND_BODY_COLUMNS

sand_body_table = Table(
    "sand_body",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "completion_interval_id",
        Integer,
        ForeignKey("completion_interval.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    # 1-based submission order within the completion interval. NOT used for
    # referential integrity -- purely so GET can reconstruct the same
    # "Sand Body 1, 2, ..." order the form submitted.
    Column("ordinal", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    *SAND_BODY_COLUMNS,
    UniqueConstraint("completion_interval_id", "ordinal", name="uq_sand_body_ci_ordinal"),
)


class SandBody(Base):
    __table__ = sand_body_table

    completion_interval = relationship("CompletionInterval", back_populates="sand_bodies")
