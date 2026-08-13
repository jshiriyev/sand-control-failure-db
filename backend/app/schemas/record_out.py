"""Response shape for GET /records/{id} -- mirrors RecordIngest's nested
Category -> Subcategory -> Parameter -> value shape, built by
db.mapping.build_record_out().
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

Bucket = dict[str, dict[str, dict[str, Any]]]


class SandBodyOut(BaseModel):
    ordinal: int
    fields: Bucket


class CompletionIntervalOut(BaseModel):
    ordinal: int
    fields: Bucket
    sand_bodies: list[SandBodyOut]


class RecordOut(BaseModel):
    id: int
    organization_id: int
    created_at: datetime
    submitted_at: datetime | None
    well: Bucket
    completion_intervals: list[CompletionIntervalOut]
