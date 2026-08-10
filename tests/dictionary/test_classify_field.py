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
    spec = classify_field(_row(input_type="Dropdown Menu", data_validation='{"A", "B"}'))
    assert spec.kind == "select"
    assert spec.options == ["A", "B"]


def test_boolean_uses_own_options_when_present():
    spec = classify_field(_row(input_type="Boolean", data_validation='{"Yes", "No"}'))
    assert spec.kind == "select"
    assert spec.options == ["Yes", "No"]


def test_boolean_falls_back_to_yes_no_when_data_validation_blank():
    spec = classify_field(_row(input_type="Boolean", data_validation=""))
    assert spec.options == ["Yes", "No"]


def test_short_date():
    spec = classify_field(_row(input_type="Short Date"))
    assert spec.kind == "date"


def test_number_positive():
    spec = classify_field(_row(input_type="Number", data_validation='{"Positive Number"}'))
    assert spec.kind == "number"
    assert spec.min_value == 0
    assert spec.step is None


def test_number_unconstrained():
    spec = classify_field(_row(input_type="Number", data_validation='{"Number"}'))
    assert spec.min_value is None


def test_number_positive_integer_with_min_max():
    spec = classify_field(_row(input_type="Number", data_validation='{"Positive Integer": {"min": 1, "max": 10}}'))
    assert spec.kind == "number"
    assert spec.min_value == 1
    assert spec.max_value == 10
    assert spec.step == 1


def test_number_required():
    spec = classify_field(_row(input_type="Number", data_validation='{"Positive Integer": {"required": True}}'))
    assert spec.required is True


def test_plain_text():
    spec = classify_field(_row(input_type="Text", data_validation=""))
    assert spec.kind == "text"


def test_multi_number_text():
    spec = classify_field(_row(
        input_type="Text", parameter="Mud PSD",
        unit="D10 / D50 / D90", data_validation='{"Number / Number / Number"}',
    ))
    assert spec.kind == "multi_number"
    assert spec.multi_labels == ["D10", "D50", "D90"]


def test_unrecognized_input_type_defaults_to_text():
    spec = classify_field(_row(input_type="Something New"))
    assert spec.kind == "text"
