"""Pydantic models for the record-submission payload.

The shape is inherently Category -> Subcategory -> Parameter -> value --
exactly what the form's own "Export as JSON" button produces -- so it's
modeled as generic nested dicts rather than ~145 named fields.
db/mapping.py's field_registry-driven flatten_bucket() is what actually
knows what a valid bucket looks like (see schemas/validation.py).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.schemas.validation import validate_bucket

Bucket = dict[str, dict[str, dict[str, Any]]]
CommentBucket = dict[str, dict[str, dict[str, str]]]


class CompletionIntervalComments(BaseModel):
    fields: CommentBucket = Field(default_factory=dict)
    sand_bodies: list[CommentBucket] = Field(default_factory=list)


class RecordComments(BaseModel):
    well: CommentBucket = Field(default_factory=dict)
    completion_intervals: list[CompletionIntervalComments] = Field(default_factory=list)



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
    record_status: Literal["draft", "complete"] | None = None
    well: Bucket = Field(default_factory=dict)
    completion_intervals: list[CompletionIntervalIngest] = Field(min_length=1)
    comments: RecordComments | None = None

    @field_validator("well")
    @classmethod
    def _validate_well(cls, v: Bucket) -> Bucket:
        return validate_bucket(v, scope="well")

    @model_validator(mode="after")
    def _validate_comment_layout(self) -> "RecordIngest":
        # The static form saves incomplete files locally, but this endpoint
        # creates submitted records. An explicit draft marker is therefore a
        # useful final guard even when a particular draft happens to contain
        # enough required values to pass field validation.
        if self.record_status == "draft":
            raise ValueError("Draft files cannot be submitted as completed records")
        if self.comments is None:
            return self
        if len(self.comments.completion_intervals) != len(self.completion_intervals):
            raise ValueError("Comment groups must match completion intervals")
        for interval, notes in zip(self.completion_intervals, self.comments.completion_intervals):
            if len(notes.sand_bodies) != len(interval.sand_bodies):
                raise ValueError("Comment groups must match sand bodies")
        return self


class RecordCreated(BaseModel):
    id: int
