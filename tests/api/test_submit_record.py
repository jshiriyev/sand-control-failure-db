"""POST /records: happy path + validation failures.

The set of required dictionary fields is driven by ``MASTER.xlsx`` and can
change on any dictionary revision, so the minimal valid payload every test
here starts from is built from ``field_registry.json`` by the ``make_payload``
fixture (see ``tests/conftest.py``) rather than hand-maintained.
"""
from __future__ import annotations


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_submit_happy_path_creates_rows_in_all_three_tables(client, seeded_org, db_session, make_payload):
    org, token = seeded_org
    payload = make_payload()
    payload["well"]["Well Specific"]["Well & Field Identification"]["Well name (anonymized)"] = "TESTWELL1"
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    record_id = resp.json()["id"]

    from db.models import Well

    well = db_session.get(Well, record_id)
    assert well is not None
    assert well.organization_id == org.id
    assert well.well_name_anonymized == "TESTWELL1"
    assert len(well.completion_intervals) == 1
    assert len(well.completion_intervals[0].sand_bodies) == 1


def test_submit_missing_required_field_returns_422(client, seeded_org, make_payload):
    _, token = seeded_org
    payload = make_payload()
    del payload["well"]["Well Specific"]["Well & Field Identification"]["Well name (anonymized)"]
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422
    assert "required" in resp.text.lower()


def test_submit_unknown_parameter_returns_422(client, seeded_org, make_payload):
    _, token = seeded_org
    payload = make_payload()
    payload["well"]["Well Specific"]["Well & Field Identification"]["Not A Real Field"] = "x"
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422


def test_submit_invalid_dropdown_value_returns_422(client, seeded_org, make_payload):
    _, token = seeded_org
    payload = make_payload()
    payload["well"]["Well Specific"]["Well & Field Identification"]["Operating environment"] = "Mars"
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422


def test_submit_out_of_range_number_returns_422(client, seeded_org, make_payload):
    _, token = seeded_org
    payload = make_payload()
    payload["well"]["Completion Intervals"] = {"Completion Intervals": {"Number of Completion Intervals": 999}}
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422


def test_submit_multi_number_splits_into_columns(client, seeded_org, db_session, make_payload):
    _, token = seeded_org
    payload = make_payload()
    payload["completion_intervals"][0]["fields"].setdefault("Completion", {})["OH Drilling Details"] = {
        "Mud PSD D10/D25/D40/D50/D75/D90": [10, 25, 40, 50, 75, 90]
    }
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text

    from db.models import Well

    well = db_session.get(Well, resp.json()["id"])
    ci = well.completion_intervals[0]
    assert float(ci.mud_psd_d10) == 10
    assert float(ci.mud_psd_d25) == 25
    assert float(ci.mud_psd_d40) == 40
    assert float(ci.mud_psd_d50) == 50
    assert float(ci.mud_psd_d75) == 75
    assert float(ci.mud_psd_d90) == 90


def test_submit_yes_no_normalizes_to_boolean(client, seeded_org, db_session, make_payload):
    _, token = seeded_org
    payload = make_payload()
    payload["well"]["Well Specific"]["Failure Confirmation"] = {"Sand failure": "Yes"}
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text

    from db.models import Well

    well = db_session.get(Well, resp.json()["id"])
    assert well.sand_failure is True


def test_submit_requires_at_least_one_completion_interval(client, seeded_org, make_payload):
    _, token = seeded_org
    payload = make_payload()
    payload["completion_intervals"] = []
    resp = client.post("/records", json=payload, headers=_auth(token))
    assert resp.status_code == 422
