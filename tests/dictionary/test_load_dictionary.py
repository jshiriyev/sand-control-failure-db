"""Loads the REAL MASTER.xlsx and asserts structural invariants the rest of
the pipeline (form generator, db codegen) depends on. If a future
dictionary edit breaks one of these, this test is meant to fail loudly here
rather than let a downstream generator silently misbehave.
"""
from __future__ import annotations

from pathlib import Path

from dictionary import COMPLETION_SCOPE, SAND_BODY_SCOPE, WELL_SCOPE, load_dictionary

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MASTER_XLSX = REPO_ROOT / "MASTER.xlsx"


def test_master_xlsx_exists():
    assert MASTER_XLSX.exists(), "MASTER.xlsx must exist at the repo root"


def test_loads_a_substantial_number_of_rows():
    rows = load_dictionary(MASTER_XLSX)
    assert len(rows) > 100


def test_every_row_has_required_fields():
    rows = load_dictionary(MASTER_XLSX)
    for row in rows:
        assert row.parameter, f"blank Parameter (category={row.category!r})"
        assert row.scope in (WELL_SCOPE, COMPLETION_SCOPE, SAND_BODY_SCOPE), (
            f"unexpected Scope {row.scope!r} on parameter {row.parameter!r}"
        )
        assert row.category, f"blank Category on parameter {row.parameter!r}"
        assert row.subcategory, f"blank Subcategory on parameter {row.parameter!r}"
        assert row.input_type, f"blank Input Type on parameter {row.parameter!r}"


def test_tooltip_is_optional_and_loads_as_blank_when_absent():
    # A Tooltip is a nice-to-have, not a requirement -- a row without one
    # loads with tooltip="" and the form simply omits its "?" icon
    # (see form/generate_form.py:render_field_row's `if row.tooltip` check).
    rows = load_dictionary(MASTER_XLSX)
    for r in rows:
        assert isinstance(r.tooltip, str)


def test_no_duplicate_parameter_within_same_category_subcategory():
    rows = load_dictionary(MASTER_XLSX)
    seen = set()
    dupes = []
    for r in rows:
        key = (r.category, r.subcategory, r.parameter)
        if key in seen:
            dupes.append(key)
        seen.add(key)
    assert not dupes, f"duplicate (Category, Subcategory, Parameter) rows: {dupes}"


def test_no_leading_or_trailing_whitespace():
    rows = load_dictionary(MASTER_XLSX)
    for r in rows:
        for field_name in ("category", "subcategory", "parameter", "scope"):
            value = getattr(r, field_name)
            assert value == value.strip(), f"{field_name} has leading/trailing whitespace: {value!r}"
