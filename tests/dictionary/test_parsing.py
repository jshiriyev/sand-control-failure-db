"""Unit tests for dictionary.parsing against representative cell strings
(not the real MASTER.xlsx -- see test_load_dictionary.py for that)."""
from __future__ import annotations

from dictionary.parsing import (
    parse_affected_cell,
    parse_dropdown_options,
    parse_multi_number,
    parse_validation_cell,
    safe_literal,
)


def test_safe_literal_valid():
    assert safe_literal('{"A", "B"}') == {"A", "B"}
    assert safe_literal('{"min": 1, "max": 10}') == {"min": 1, "max": 10}
    assert safe_literal("None") is None


def test_safe_literal_tolerates_lowercase_json_booleans_and_null():
    assert safe_literal('{"min": 1, "required": true}') == {"min": 1, "required": True}
    assert safe_literal('{"required": false}') == {"required": False}
    assert safe_literal('{"min": null}') == {"min": None}


def test_safe_literal_invalid_returns_none():
    assert safe_literal("not a literal {") is None
    assert safe_literal("") is None
    assert safe_literal(None) is None


def test_parse_validation_cell_bare_type():
    assert parse_validation_cell('{"Decimal"}') == {
        "type": "Decimal", "options": None, "min": None, "max": None, "required": False, "pattern": None,
        "length": None,
    }


def test_parse_validation_cell_with_modifiers():
    assert parse_validation_cell('{"Whole number": {"min": 1, "max": 10}}') == {
        "type": "Whole number", "options": None, "min": 1, "max": 10, "required": False, "pattern": None,
        "length": None,
    }


def test_parse_validation_cell_required():
    spec = parse_validation_cell('{"Whole number": {"required": True, "min": 0}}')
    assert spec["required"] is True
    assert spec["min"] == 0


def test_parse_validation_cell_list():
    assert parse_validation_cell('{"List": ["Zebra", "Apple", "Mango"]}') == {
        "type": "List", "options": ["Zebra", "Apple", "Mango"], "min": None, "max": None, "required": False,
        "pattern": None, "length": None,
    }


def test_parse_validation_cell_list_options_nested():
    # Current MASTER.xlsx shape -- options live under "options" so other
    # modifiers (e.g. "required") can sit alongside them.
    assert parse_validation_cell('{"List": {"options": ["Zebra", "Apple"], "required": True}}') == {
        "type": "List", "options": ["Zebra", "Apple"], "min": None, "max": None, "required": True,
        "pattern": None, "length": None,
    }


def test_parse_validation_cell_text_with_length_and_pattern():
    # Current MASTER.xlsx shape for a length-constrained Text field, e.g.
    # the anonymized well identification number.
    assert parse_validation_cell('{"Text": {"length": 7, "pattern": "alphanumeric", "required": True}}') == {
        "type": "Text", "options": None, "min": None, "max": None, "required": True,
        "pattern": "alphanumeric", "length": 7,
    }


def test_parse_validation_cell_any_value():
    assert parse_validation_cell('{"Any Value": {}}') == {
        "type": "Any Value", "options": None, "min": None, "max": None, "required": False, "pattern": None,
        "length": None,
    }


def test_parse_validation_cell_blank():
    assert parse_validation_cell("") is None
    assert parse_validation_cell(None) is None


def test_parse_validation_cell_multi_number_malformed_bracket_shape():
    # The real sheet's multi-number cells look like this: not valid literal
    # syntax on their own, recovered segment by segment.
    specs = parse_validation_cell('{["Decimal": {"min": 0}, "Decimal": {"min": 0}, "Decimal": {"min": 0}]}')
    assert specs == [
        {"type": "Decimal", "options": None, "min": 0, "max": None, "required": False, "pattern": None, "length": None},
        {"type": "Decimal", "options": None, "min": 0, "max": None, "required": False, "pattern": None, "length": None},
        {"type": "Decimal", "options": None, "min": 0, "max": None, "required": False, "pattern": None, "length": None},
    ]


def test_parse_validation_cell_multi_number_well_formed_list_shape():
    # A cleanly-written list-of-specs is supported too, not just the
    # malformed wrapper the current sheet happens to use.
    specs = parse_validation_cell('[{"Decimal": {"min": 0}}, {"Whole number": {"min": 1}}]')
    assert specs == [
        {"type": "Decimal", "options": None, "min": 0, "max": None, "required": False, "pattern": None, "length": None},
        {
            "type": "Whole number", "options": None, "min": 1, "max": None, "required": False,
            "pattern": None, "length": None,
        },
    ]


def test_parse_dropdown_options_preserves_source_order():
    assert parse_dropdown_options('{"List": ["Zebra", "Apple", "Mango"]}') == ["Zebra", "Apple", "Mango"]


def test_parse_dropdown_options_empty():
    assert parse_dropdown_options("") == []
    assert parse_dropdown_options(None) == []
    assert parse_dropdown_options('{"Decimal"}') == []


def test_parse_multi_number_labels_from_unit():
    result = parse_multi_number(
        '{["Decimal": {"min": 0}, "Decimal": {"min": 0}, "Decimal": {"min": 0}]}', "D10 / D50 / D90", "Mud PSD",
    )
    assert result is not None
    labels, specs = result
    assert labels == ["D10", "D50", "D90"]
    assert len(specs) == 3
    assert all(s["min"] == 0 for s in specs)


def test_parse_multi_number_labels_from_parameter_suffix_when_unit_mismatched():
    raw = '{[' + ", ".join(['"Decimal": {"min": 0}'] * 6) + ']}'
    labels, _specs = parse_multi_number(
        raw, "microns", "Particle Size Distribution D10/D25/D40/D50/D75/D90",
    )
    assert labels == ["D10", "D25", "D40", "D50", "D75", "D90"]


def test_parse_multi_number_generic_fallback():
    raw = '{["Decimal": {}, "Decimal": {}]}'
    labels, _specs = parse_multi_number(raw, "", "Some Pair")
    assert labels == ["Value 1", "Value 2"]


def test_parse_multi_number_not_a_multi_field():
    assert parse_multi_number('{"Decimal": {"min": 0}}', "ft", "Water depth") is None
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
