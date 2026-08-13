"""Shared parser for the Sand Control Failure Data Dictionary (MASTER.xlsx).

This package is the single place that knows how to read MASTER.xlsx and
interpret its DSL (Data Validation / Affected Subcategory / Affected
Parameter cells). It has no knowledge of HTML or SQL -- form/generate_form.py
and db/codegen.py both import from here so the dictionary stays the one
source of truth for what a cell means, instead of each consumer maintaining
its own interpretation.
"""
from dictionary.classify import classify_field
from dictionary.grouping import group_by_category_subcategory
from dictionary.loader import SHEET_NAME, load_dictionary
from dictionary.models import (
    COMPLETION_SCOPE,
    SAND_BODY_SCOPE,
    WELL_SCOPE,
    FieldSpec,
    ParamRow,
)
from dictionary.parsing import (
    MULTI_LABEL_SUFFIX_RE,
    parse_affected_cell,
    parse_dropdown_options,
    parse_multi_number,
    parse_validation_cell,
    safe_literal,
)

__all__ = [
    "COMPLETION_SCOPE",
    "MULTI_LABEL_SUFFIX_RE",
    "SAND_BODY_SCOPE",
    "SHEET_NAME",
    "WELL_SCOPE",
    "FieldSpec",
    "ParamRow",
    "classify_field",
    "group_by_category_subcategory",
    "load_dictionary",
    "parse_affected_cell",
    "parse_dropdown_options",
    "parse_multi_number",
    "parse_validation_cell",
    "safe_literal",
]
