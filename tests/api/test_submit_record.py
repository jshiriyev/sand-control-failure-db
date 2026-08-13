"""POST /records: happy path + validation failures.

"Well identification number" is the only dictionary field currently marked
required, so it's the one field every minimal valid payload here must set.
"""
from __future__ import annotations

import copy


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _minimal_valid_payload() -> dict:
    return {
        "well": {
            "Well Specific": {
                "Well & Field Identification": {
                    "Well name": "TEST-WELL-1",
                    "Well identification number": 12345,
                }
            }
        },
        "completion_intervals": [
            {"fields": {}, "sand_bodies": [{}]},
        ],
    }


def test_submit_happy_path_creates_rows_in_all_three_tables(client, seeded_org, db_session):
    org, token = seeded_org
    resp = client.post("/records", json=_minimal_valid_payload(), headers=_auth(token))
    assert resp.status_code == 201, resp.text
    record_id = resp.json()["id"]

    from db.models import Well

    well = db_session.get(Well, record_id)
    assert well is not None
    assert well.organization_id == org.id
    assert well.well_name == "TEST-WELL-1"
    assert len(well.completion_intervals) == 1
    assert len(well.completion_intervals[0].sand_bodies) == 1


def test_submit_missing_required_field_returns_422(client, seeded_org):
    _, token = seeded_org
    payload = _minimal_valid_payload()
    del payload["well"]["Well Specific"]["Well & Field Identification"]["Well identification number"]
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422
    assert "required" in resp.text.lower()


def test_submit_unknown_parameter_returns_422(client, seeded_org):
    _, token = seeded_org
    payload = _minimal_valid_payload()
    payload["well"]["Well Specific"]["Well & Field Identification"]["Not A Real Field"] = "x"
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422


def test_submit_invalid_dropdown_value_returns_422(client, seeded_org):
    _, token = seeded_org
    payload = _minimal_valid_payload()
    payload["well"]["Well Specific"]["Well & Field Identification"]["Operating environment"] = "Mars"
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422


def test_submit_out_of_range_number_returns_422(client, seeded_org):
    _, token = seeded_org
    payload = _minimal_valid_payload()
    payload["well"]["Completion Intervals"] = {"Completion Intervals": {"Number of Completion Intervals": 999}}
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422


def test_submit_multi_number_splits_into_columns(client, seeded_org, db_session):
    _, token = seeded_org
    payload = copy.deepcopy(_minimal_valid_payload())
    payload["completion_intervals"][0]["fields"] = {"Drilling": {"Drilling Details": {"Mud PSD": [10, 50, 90]}}}
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text

    from db.models import Well

    well = db_session.get(Well, resp.json()["id"])
    ci = well.completion_intervals[0]
    assert float(ci.mud_psd_value_1) == 10
    assert float(ci.mud_psd_value_2) == 50
    assert float(ci.mud_psd_value_3) == 90


def test_submit_yes_no_normalizes_to_boolean(client, seeded_org, db_session):
    _, token = seeded_org
    payload = copy.deepcopy(_minimal_valid_payload())
    payload["well"]["Well Specific"]["Failure Confirmation"] = {"Sand failure": "Yes"}
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text

    from db.models import Well

    well = db_session.get(Well, resp.json()["id"])
    assert well.sand_failure is True


def test_submit_requires_at_least_one_completion_interval(client, seeded_org):
    _, token = seeded_org
    payload = _minimal_valid_payload()
    payload["completion_intervals"] = []
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422
