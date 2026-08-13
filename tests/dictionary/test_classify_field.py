"""classify_field() maps Input Type + Data Validation to the expected FieldSpec."""
from __future__ import annotations

from dictionary.classify import classify_field
from dictionary.models import ParamRow


def _row(**overrides) -> ParamRow:
    base = dict(
        scope="Well", category="C", subcategory="S", parameter="P",
        input_type="Text", unit="", affected_subcategory="", affected_parameter="",
        data_validation="", tooltip="t", user_comment="",
    )
    base.update(overrides)
    return ParamRow(**base)


def test_dropdown_menu():
    spec = classify_field(_row(input_type="Dropdown Menu", data_validation='{"List": ["A", "B"]}'))
    assert spec.kind == "select"
    assert spec.options == ["A", "B"]


def test_boolean_uses_own_options_when_present():
    spec = classify_field(_row(input_type="Boolean", data_validation='{"List": ["Yes", "No"]}'))
    assert spec.kind == "select"
    assert spec.options == ["Yes", "No"]


def test_boolean_falls_back_to_yes_no_when_data_validation_blank():
    spec = classify_field(_row(input_type="Boolean", data_validation=""))
    assert spec.options == ["Yes", "No"]


def test_short_date():
    spec = classify_field(_row(input_type="Short Date", data_validation='{"Short Date"}'))
    assert spec.kind == "date"


def test_number_decimal_unconstrained():
    spec = classify_field(_row(input_type="Number", data_validation='{"Decimal"}'))
    assert spec.kind == "number"
    assert spec.min_value is None
    assert spec.step is None


def test_number_decimal_with_min():
    spec = classify_field(_row(input_type="Number", data_validation='{"Decimal": {"min": 0}}'))
    assert spec.kind == "number"
    assert spec.min_value == 0
    assert spec.step is None


def test_number_whole_number_with_min_max():
    spec = classify_field(_row(input_type="Number", data_validation='{"Whole number": {"min": 1, "max": 10}}'))
    assert spec.kind == "number"
    assert spec.min_value == 1
    assert spec.max_value == 10
    assert spec.step == 1


def test_number_required():
    spec = classify_field(_row(input_type="Number", data_validation='{"Whole number": {"required": True, "min": 0}}'))
    assert spec.required is True


def test_number_blank_data_validation():
    spec = classify_field(_row(input_type="Number", data_validation=""))
    assert spec.min_value is None
    assert spec.step is None


def test_plain_text():
    spec = classify_field(_row(input_type="Text", data_validation='{"Any Value": {}}'))
    assert spec.kind == "text"


def test_text_blank_data_validation():
    spec = classify_field(_row(input_type="Text", data_validation=""))
    assert spec.kind == "text"


def test_multi_number_text():
    raw = '{["Decimal": {"min": 0}, "Decimal": {"min": 0}, "Decimal": {"min": 0}]}'
    spec = classify_field(_row(
        input_type="Text", parameter="Mud PSD", unit="D10 / D50 / D90", data_validation=raw,
    ))
    assert spec.kind == "multi_number"
    assert spec.multi_labels == ["D10", "D50", "D90"]
    assert spec.multi_min_values == [0, 0, 0]


def test_unrecognized_input_type_defaults_to_text():
    spec = classify_field(_row(input_type="Something New"))
    assert spec.kind == "text"
