"""Unit tests for dictionary.parsing against representative cell strings
(not the real MASTER.xlsx -- see test_load_dictionary.py for that)."""
from __future__ import annotations

from dictionary.parsing import (
    parse_affected_cell,
    parse_dropdown_options,
    parse_multi_number,
    parse_number_spec,
    safe_literal,
)


def test_safe_literal_valid():
    assert safe_literal('{"A", "B"}') == {"A", "B"}
    assert safe_literal('{"min": 1, "max": 10}') == {"min": 1, "max": 10}
    assert safe_literal("None") is None


def test_safe_literal_invalid_returns_none():
    assert safe_literal("not a literal {") is None
    assert safe_literal("") is None
    assert safe_literal(None) is None


def test_parse_dropdown_options_preserves_source_order():
    # ast.literal_eval would give an unordered set -- must not rely on that.
    assert parse_dropdown_options('{"Zebra", "Apple", "Mango"}') == ["Zebra", "Apple", "Mango"]


def test_parse_dropdown_options_empty():
    assert parse_dropdown_options("") == []
    assert parse_dropdown_options(None) == []


def test_parse_number_spec_positive():
    assert parse_number_spec('{"Positive Number"}') == {"min_value": 0}


def test_parse_number_spec_plain_number():
    assert parse_number_spec('{"Number"}') == {}


def test_parse_number_spec_positive_integer_with_min_max():
    assert parse_number_spec('{"Positive Integer": {"min": 1, "max": 10}}') == {
        "min_value": 1,
        "max_value": 10,
        "step": 1,
    }


def test_parse_number_spec_required():
    assert parse_number_spec('{"Positive Integer": {"required": True}}') == {
        "min_value": 0,
        "step": 1,
        "required": True,
    }


def test_parse_number_spec_blank():
    assert parse_number_spec("") == {}


def test_parse_multi_number_labels_from_unit():
    labels = parse_multi_number('{"Number / Number / Number"}', "D10 / D50 / D90", "Mud PSD")
    assert labels == ["D10", "D50", "D90"]


def test_parse_multi_number_labels_from_parameter_suffix_when_unit_mismatched():
    labels = parse_multi_number(
        '{"Number / Number / Number / Number / Number / Number"}',
        "microns",
        "Particle Size Distribution D10/D25/D40/D50/D75/D90",
    )
    assert labels == ["D10", "D25", "D40", "D50", "D75", "D90"]


def test_parse_multi_number_generic_fallback():
    labels = parse_multi_number('{"Number / Number"}', "", "Some Pair")
    assert labels == ["Value 1", "Value 2"]


def test_parse_multi_number_not_a_multi_field():
    assert parse_multi_number('{"Positive Number"}', "ft", "Water depth") is None
    assert parse_multi_number("", "", "Anything") is None


def test_parse_affected_cell_show_convention():
    rules = parse_affected_cell('{"Yes": {"Failure Details & Performance Impact"}}')
    assert rules == [("Yes", "Failure Details & Performance Impact", False)]


def test_parse_affected_cell_hide_convention():
    rules = parse_affected_cell('{"Onshore": {"Water depth": False, "Tree type": False}}')
    assert set(rules) == {("Onshore", "Water depth", True), ("Onshore", "Tree type", True)}


def test_parse_affected_cell_multiple_triggers():
    rules = parse_affected_cell('{"Open Hole": {"Open Hole Details"}, "Cased Hole": {"Cased Hole Details"}}')
    assert set(rules) == {
        ("Open Hole", "Open Hole Details", False),
        ("Cased Hole", "Cased Hole Details", False),
    }


def test_parse_affected_cell_empty():
    assert parse_affected_cell("") == []
    assert parse_affected_cell(None) == []
