"""Pydantic models for the record-submission payload.

The shape is inherently Category -> Subcategory -> Parameter -> value --
exactly what the form's own "Export as JSON" button produces -- so it's
modeled as generic nested dicts rather than ~145 named fields.
db/mapping.py's field_registry-driven flatten_bucket() is what actually
knows what a valid bucket looks like (see schemas/validation.py).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.validation import validate_bucket

Bucket = dict[str, dict[str, dict[str, Any]]]


class CompletionIntervalIngest(BaseModel):
    fields: Bucket = Field(default_factory=dict)
    sand_bodies: list[Bucket] = Field(default_factory=list)

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, v: Bucket) -> Bucket:
        return validate_bucket(v, scope="completion_interval")

    @field_validator("sand_bodies")
    @classmethod
    def _validate_sand_bodies(cls, v: list[Bucket]) -> list[Bucket]:
        return [validate_bucket(item, scope="sand_body") for item in v]


class RecordIngest(BaseModel):
    generated_at: datetime | None = None
    well: Bucket = Field(default_factory=dict)
    completion_intervals: list[CompletionIntervalIngest] = Field(min_length=1)

    @field_validator("well")
    @classmethod
    def _validate_well(cls, v: Bucket) -> Bucket:
        return validate_bucket(v, scope="well")


class RecordCreated(BaseModel):
    id: int
