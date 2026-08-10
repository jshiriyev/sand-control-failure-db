"""Maps a dictionary row's Input Type + Data Validation into a typed FieldSpec."""
from __future__ import annotations

from dictionary.models import FieldSpec, ParamRow
from dictionary.parsing import parse_dropdown_options, parse_multi_number, parse_number_spec


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
        return FieldSpec(kind="number", **parse_number_spec(row.data_validation))
    if it == "Text":
        labels = parse_multi_number(row.data_validation, row.unit, row.parameter)
        if labels:
            return FieldSpec(kind="multi_number", multi_labels=labels)
        return FieldSpec(kind="text")
    return FieldSpec(kind="text")
