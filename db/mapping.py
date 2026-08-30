"""Translates between the nested Category -> Subcategory -> Parameter -> value
JSON shape (exactly what the form's "Export as JSON" button produces) and the
flat {db_column: python_value} dicts the ORM models need -- in both
directions, driven entirely by db/generated/field_registry.json so there is
exactly one place that knows what a bucket means.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "generated" / "field_registry.json"

_TRUE_STRINGS = {"yes", "true"}


class MappingError(ValueError):
    """Raised with every problem found in a bucket, not just the first."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _load_registry() -> dict[str, dict]:
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        return json.load(f)


_REGISTRY = _load_registry()
_BY_SCOPE: dict[str, dict[str, dict]] = {}
for _key, _entry in _REGISTRY.items():
    _scope, _rest = _key.split("::", 1)
    _BY_SCOPE.setdefault(_scope, {})[_rest] = _entry


def _coerce(entry: dict, leaf_key: str, value: Any, errors: list[str]) -> dict[str, Any]:
    """Coerces one leaf `value` per its registry entry; returns {db_column: value}
    (a multi_number field can populate more than one column)."""
    if value is None or value == "":
        return {}

    kind = entry["kind"]
    db_type = entry["db_type"]
    columns = entry["db_columns"]

    if kind == "select":
        text_value = str(value)
        options = entry["options"]
        if options and text_value not in options:
            errors.append(f"{leaf_key}: {value!r} is not one of {options}")
            return {}
        if db_type == "Boolean":
            return {columns[0]: text_value.lower() in _TRUE_STRINGS}
        return {columns[0]: text_value}

    if kind == "text":
        text_value = str(value)
        if entry.get("min_length") is not None and len(text_value) < entry["min_length"]:
            errors.append(f"{leaf_key}: {value!r} is shorter than the minimum length {entry['min_length']}")
            return {}
        if entry.get("max_length") is not None and len(text_value) > entry["max_length"]:
            errors.append(f"{leaf_key}: {value!r} is longer than the maximum length {entry['max_length']}")
            return {}
        if entry.get("pattern") and not re.match(entry["pattern"], text_value):
            errors.append(f"{leaf_key}: {value!r} does not match the required format")
            return {}
        return {columns[0]: text_value}

    if kind == "number":
        number = _to_number(value, db_type)
        if number is None:
            errors.append(f"{leaf_key}: {value!r} is not a valid number")
            return {}
        if entry["min_value"] is not None and number < entry["min_value"]:
            errors.append(f"{leaf_key}: {value!r} is below the minimum {entry['min_value']}")
            return {}
        if entry["max_value"] is not None and number > entry["max_value"]:
            errors.append(f"{leaf_key}: {value!r} is above the maximum {entry['max_value']}")
            return {}
        return {columns[0]: number}

    if kind == "date":
        try:
            return {columns[0]: date.fromisoformat(str(value))}
        except ValueError:
            errors.append(f"{leaf_key}: {value!r} is not a YYYY-MM-DD date")
            return {}

    if kind == "multi_number":
        if not isinstance(value, (list, tuple)) or len(value) != len(columns):
            errors.append(f"{leaf_key}: expected {len(columns)} values, got {value!r}")
            return {}
        out: dict[str, Any] = {}
        for column, sub_value in zip(columns, value):
            if sub_value in (None, ""):
                continue
            number = _to_number(sub_value, db_type)
            if number is None:
                errors.append(f"{leaf_key}: {sub_value!r} is not a valid number")
                continue
            out[column] = number
        return out

    errors.append(f"{leaf_key}: unrecognized field kind {kind!r}")
    return {}


def _to_number(value: Any, db_type: str) -> int | Decimal | None:
    try:
        return int(value) if db_type == "Integer" else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def flatten_bucket(bucket: dict[str, dict[str, dict[str, Any]]], scope: str) -> dict[str, Any]:
    """Category -> Subcategory -> Parameter -> value, validated against the
    dictionary-derived registry for `scope`, flattened into {db_column: value}.
    Raises MappingError (with every problem found, not just the first) if any
    parameter is unrecognized or any value fails validation.
    """
    index = _BY_SCOPE.get(scope, {})
    flat: dict[str, Any] = {}
    errors: list[str] = []
    provided_keys: set[str] = set()

    for category, subcats in (bucket or {}).items():
        for subcategory, params in (subcats or {}).items():
            for parameter, value in (params or {}).items():
                leaf_key = f"{category} / {subcategory} / {parameter}"
                key = f"{category}::{subcategory}::{parameter}"
                entry = index.get(key)
                if entry is None:
                    errors.append(f"{leaf_key}: not a recognized field for this record level")
                    continue
                coerced = _coerce(entry, leaf_key, value, errors)
                if coerced:
                    provided_keys.add(key)
                flat.update(coerced)

    for key, entry in index.items():
        if entry.get("required") and key not in provided_keys:
            errors.append(
                f"{entry['category']} / {entry['subcategory']} / {entry['parameter']}: this field is required"
            )

    if errors:
        raise MappingError(errors)
    return flat


def build_record_out(row_values: dict[str, Any], scope: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Inverse of flatten_bucket: given {db_column: value} for one ORM row,
    regroups into Category -> Subcategory -> Parameter -> value, re-merging
    multi_number sub-columns and re-serializing dates/Decimals/bools back to
    the same JSON-friendly representation the form itself emits.
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for entry in _REGISTRY.values():
        if entry["scope"] != scope:
            continue
        columns = entry["db_columns"]
        if entry["kind"] == "multi_number":
            if all(row_values.get(c) is None for c in columns):
                continue
            value: Any = [_serialize(row_values.get(c)) for c in columns]
        else:
            raw = row_values.get(columns[0])
            if raw is None:
                continue
            value = _serialize(raw)
        cat_bucket = out.setdefault(entry["category"], {})
        subcat_bucket = cat_bucket.setdefault(entry["subcategory"], {})
        subcat_bucket[entry["parameter"]] = value
    return out


def _serialize(value: Any) -> Any:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
