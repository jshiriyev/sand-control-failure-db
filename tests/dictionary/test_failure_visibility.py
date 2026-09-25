"""Protect the representative's Yes/No field sets after merging the sections.

The published row lists predate deletion of old row 18, so every affected
row number after severity is one lower in the current workbook.
"""
from __future__ import annotations

from db.mapping import _REGISTRY

YES_ONLY = set(range(18, 25)) | set(range(32, 37)) | set(range(41, 47))
SHARED = set(range(28, 32)) | set(range(37, 41)) | set(range(47, 58))


def test_failure_confirmation_only_controls_its_extra_questions():
    well = [entry for entry in _REGISTRY.values() if entry["scope"] == "well"]
    merged = [entry for entry in well if entry["subcategory"] == "Sand Production & Well Performance"]
    assert {entry["row_number"] for entry in merged if any(
        rule["parameter"] == "Sand failure" for rule in entry.get("visibility", {}).get("show", [])
    )} == YES_ONLY
    for entry in merged:
        visibility = entry.get("visibility", {})
        assert not visibility.get("subcategory_show")
        assert not visibility.get("subcategory_hide")
        if entry["row_number"] in SHARED | {17}:
            assert not any(rule["parameter"] == "Sand failure" for rule in visibility.get("show", []))


def test_severity_is_one_required_type_controlled_field():
    severity = [entry for entry in _REGISTRY.values() if entry["parameter"] == "Severity of sand production"]
    assert len(severity) == 1
    entry = severity[0]
    assert entry["required"]
    assert {rule["parameter"] for rule in entry["visibility"]["show"]} == {"Well type"}
    assert {rule["value"] for rule in entry["visibility"]["show"]} == {
        "Oil Producer", "Gas Producer", "Gas Condensate Producer",
    }
    assert "lb/MMSCF" not in " ".join(entry["options_by"]["Well type"]["Oil Producer"])


def test_sand_rates_still_depend_on_measurable_quantification():
    rows = [entry for entry in _REGISTRY.values() if 25 <= entry["row_number"] <= 27]
    assert len(rows) == 3
    for entry in rows:
        assert entry["visibility"]["show"] == [
            {"parameter": "Sand rate quantification", "value": "Measurable"},
        ]
