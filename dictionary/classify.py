"""Maps a dictionary row's Input Type + Data Validation into a typed FieldSpec."""
from __future__ import annotations

from dictionary.models import FieldSpec, ParamRow
from dictionary.parsing import parse_dropdown_options, parse_multi_number, parse_validation_cell

# Named tokens a Text cell's "pattern" modifier can use instead of a raw
# regex, so a non-engineer can write `"pattern": "alphanumeric"` in Excel
# rather than hand-escaping a regex inside the DSL's string literal.
NAMED_PATTERNS = {
    "alphanumeric": r"^[A-Za-z0-9]+$",
}


def _number_kwargs(spec: dict | None) -> dict:
    if not isinstance(spec, dict):
        return {}
    kwargs = {"min_value": spec.get("min"), "max_value": spec.get("max"), "required": bool(spec.get("required"))}
    if str(spec.get("type", "")).strip().lower() == "whole number":
        kwargs["step"] = 1
    return kwargs


def _resolve_pattern(token: str | None) -> str | None:
    if not token:
        return None
    return NAMED_PATTERNS.get(token, token)


def classify_field(row: ParamRow) -> FieldSpec:
    it = row.input_type
    if it == "Dropdown Menu":
        spec = parse_validation_cell(row.data_validation)
        required = bool(spec.get("required")) if isinstance(spec, dict) else False
        return FieldSpec(kind="select", options=parse_dropdown_options(row.data_validation), required=required)
    if it == "Boolean":
        spec = parse_validation_cell(row.data_validation)
        required = bool(spec.get("required")) if isinstance(spec, dict) else False
        opts = parse_dropdown_options(row.data_validation)
        return FieldSpec(kind="select", options=opts or ["Yes", "No"], required=required)
    if it == "Short Date":
        spec = parse_validation_cell(row.data_validation)
        required = bool(spec.get("required")) if isinstance(spec, dict) else False
        return FieldSpec(kind="date", required=required)
    if it == "Number":
        spec = parse_validation_cell(row.data_validation)
        return FieldSpec(kind="number", **_number_kwargs(spec if isinstance(spec, dict) else None))
    if it == "Text":
        multi = parse_multi_number(row.data_validation, row.unit, row.parameter)
        if multi:
            labels, specs = multi
            return FieldSpec(
                kind="multi_number",
                multi_labels=labels,
                multi_min_values=[s.get("min") for s in specs],
                multi_max_values=[s.get("max") for s in specs],
            )
        spec = parse_validation_cell(row.data_validation)
        if isinstance(spec, dict):
            length, pattern = spec.get("length"), spec.get("pattern")
            required = bool(spec.get("required"))
            if length is not None or pattern:
                return FieldSpec(
                    kind="text", min_length=length, pattern=_resolve_pattern(pattern), required=required,
                )
            return FieldSpec(kind="text", required=required)
        return FieldSpec(kind="text")
    return FieldSpec(kind="text")
