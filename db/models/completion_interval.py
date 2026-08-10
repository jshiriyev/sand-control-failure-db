"""The `completion_interval` table -- one row per Completion Interval (sand
body) within a production interval, plus the ~82 dictionary-driven columns
generated from MASTER.xlsx's Completion-Interval-scope parameters (see
db/generated/completion_interval_columns.py, never hand-edited).
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, UniqueConstraint, func
from sqlalchemy.orm import relationship

from db.base import Base
from db.generated.completion_interval_columns import COMPLETION_INTERVAL_COLUMNS

completion_interval_table = Table(
    "completion_interval",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "production_interval_id",
        Integer,
        ForeignKey("production_interval.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("ordinal", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    *COMPLETION_INTERVAL_COLUMNS,
    UniqueConstraint("production_interval_id", "ordinal", name="uq_completion_interval_pi_ordinal"),
)


class CompletionInterval(Base):
    __table__ = completion_interval_table

    production_interval = relationship("ProductionInterval", back_populates="completion_intervals")
