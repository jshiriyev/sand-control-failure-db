"""Glue between Pydantic's per-field validation and db.mapping's
dictionary-driven bucket validation.

Pydantic validators must raise ValueError/TypeError/AssertionError to
register as a validation failure (FastAPI turns that into a 422 response);
MappingError collects every problem in a bucket at once, which is joined
into one readable message here.
"""
from __future__ import annotations

from typing import Any

from db.mapping import MappingError, flatten_bucket

Bucket = dict[str, dict[str, dict[str, Any]]]


def validate_bucket(bucket: Bucket, scope: str) -> Bucket:
    """Validates `bucket` against the dictionary-derived registry for `scope`
    and returns it unchanged if valid (raises ValueError, listing every
    problem found, otherwise). The service layer re-flattens the same bucket
    when it's ready to persist -- this function's job is purely validation,
    so db/mapping.py stays the one place that knows what a bucket means.
    """
    try:
        flatten_bucket(bucket, scope=scope)
    except MappingError as exc:
        raise ValueError("; ".join(exc.errors)) from exc
    return bucket
