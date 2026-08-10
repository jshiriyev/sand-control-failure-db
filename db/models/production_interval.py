"""The `production_interval` table -- one row per Production Interval within
a well, plus the single dictionary-driven column at that scope ("Number of
Completion Intervals" -- see db/generated/production_interval_columns.py).
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, UniqueConstraint, func
from sqlalchemy.orm import relationship

from db.base import Base
from db.generated.production_interval_columns import PRODUCTION_INTERVAL_COLUMNS

production_interval_table = Table(
    "production_interval",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("well_id", Integer, ForeignKey("well.id", ondelete="CASCADE"), nullable=False, index=True),
    # 1-based submission order within the well. NOT used for referential
    # integrity -- purely so GET can reconstruct the same "Production
    # Interval 1, 2, ..." order the form submitted.
    Column("ordinal", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    *PRODUCTION_INTERVAL_COLUMNS,
    UniqueConstraint("well_id", "ordinal", name="uq_production_interval_well_ordinal"),
)


class ProductionInterval(Base):
    __table__ = production_interval_table

    well = relationship("Well", back_populates="production_intervals")
    completion_intervals = relationship(
        "CompletionInterval",
        back_populates="production_interval",
        cascade="all, delete-orphan",
        order_by="CompletionInterval.ordinal",
    )
