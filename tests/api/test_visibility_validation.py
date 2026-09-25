"""API acceptance follows the same conditional tree as the generated form.

These tests validate records without Postgres, so a skipped database suite
cannot conceal drift between the browser and registry-driven API validation.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.schemas.ingest import RecordIngest
from dictionary import CURRENT_SCHEMA_VERSION

IDENTITY = "Well & Field Identification"
PERFORMANCE = "Sand Production & Well Performance"


def _well(payload: dict, section: str) -> dict:
    return payload["well"]["Well Specific"][section]


@pytest.mark.parametrize("failure", ["No", "Yes"])
def test_severity_is_required_for_either_failure_answer(make_payload, failure):
    payload = make_payload(sand_failure=failure)
    assert RecordIngest.model_validate(payload).well == payload["well"]
    del _well(payload, PERFORMANCE)["Severity of sand production"]
    with pytest.raises(ValidationError, match="Severity of sand production.*required"):
        RecordIngest.model_validate(payload)


@pytest.mark.parametrize("well_type", ["Oil Producer", "Gas Producer", "Gas Condensate Producer"])
def test_severity_uses_selected_well_type_choices(make_payload, well_type):
    payload = make_payload(well_type=well_type)
    severity = _well(payload, PERFORMANCE)
    assert RecordIngest.model_validate(payload)
    wrong = "Minor (<0.01 lb/MMSCF)" if well_type == "Oil Producer" else "Minor (<0.2 lb/1000 bbl)"
    severity["Severity of sand production"] = wrong
    with pytest.raises(ValidationError, match="Severity of sand production"):
        RecordIngest.model_validate(payload)


@pytest.mark.parametrize("parameter", [
    "How is sand production known?", "Sand failure mechanism", "Sand rate quantification",
])
def test_yes_only_required_questions_follow_failure_answer(make_payload, parameter):
    no_payload = make_payload(sand_failure="No")
    assert RecordIngest.model_validate(no_payload)
    yes_payload = make_payload(sand_failure="Yes")
    assert RecordIngest.model_validate(yes_payload)
    del _well(yes_payload, PERFORMANCE)[parameter]
    with pytest.raises(ValidationError, match="required"):
        RecordIngest.model_validate(yes_payload)


def test_hidden_yes_only_answer_is_rejected_for_no_failure(make_payload):
    payload = make_payload(sand_failure="No")
    _well(payload, PERFORMANCE)["Sand failure mechanism"] = "Screen Plugging"
    with pytest.raises(ValidationError, match="hidden by the current form answers"):
        RecordIngest.model_validate(payload)


def test_sand_rates_follow_nested_measurable_choice(make_payload):
    payload = make_payload(sand_failure="Yes")
    performance = _well(payload, PERFORMANCE)
    performance["Sand rate quantification"] = "Unable to quantify"
    performance["Sand production rate at first choke back"] = 1
    with pytest.raises(ValidationError, match="hidden by the current form answers"):
        RecordIngest.model_validate(payload)
    performance["Sand rate quantification"] = "Measurable"
    assert RecordIngest.model_validate(payload)


def test_offshore_required_fields_are_exempt_onshore(make_payload):
    onshore = make_payload(environment="Onshore")
    assert RecordIngest.model_validate(onshore)
    _well(onshore, IDENTITY)["Water depth"] = 100
    with pytest.raises(ValidationError, match="hidden by the current form answers"):
        RecordIngest.model_validate(onshore)

    offshore = make_payload(environment="Shelf Offshore (< 3,000 ft)")
    assert RecordIngest.model_validate(offshore)
    del _well(offshore, IDENTITY)["Tree type"]
    with pytest.raises(ValidationError, match="Tree type.*required"):
        RecordIngest.model_validate(offshore)


@pytest.mark.parametrize("version", [None, 1, "0", True])
def test_schema_version_is_explicit_and_exact(make_payload, version):
    payload = make_payload()
    if version is None:
        del payload["schema_version"]
    else:
        payload["schema_version"] = version
    with pytest.raises(ValidationError, match="schema_version"):
        RecordIngest.model_validate(payload)
    assert CURRENT_SCHEMA_VERSION == 0
