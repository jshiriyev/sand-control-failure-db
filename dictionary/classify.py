"""Maps a dictionary row's Input Type + Data Validation into a typed FieldSpec."""
from __future__ import annotations

from dictionary.models import FieldSpec, ParamRow
from dictionary.parsing import parse_dropdown_options, parse_multi_number, parse_validation_cell


def _number_kwargs(spec: dict | None) -> dict:
    if not isinstance(spec, dict):
        return {}
    kwargs = {"min_value": spec.get("min"), "max_value": spec.get("max"), "required": bool(spec.get("required"))}
    if str(spec.get("type", "")).strip().lower() == "whole number":
        kwargs["step"] = 1
    return kwargs


def classify_field(row: ParamRow) -> FieldSpec:
    it = row.input_type
    if it == "Dropdown Menu":
        return FieldSpec(kind="select", options=parse_dropdown_options(row.data_validation))
    if it == "Boolean":
        opts = parse_dropdown_options(row.data_validation)
        return FieldSpec(kind="select", options=opts or ["Yes", "No"])
    if it == "Short Date":
        return FieldSpec(kind="date")
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
        return FieldSpec(kind="text")
    return FieldSpec(kind="text")
