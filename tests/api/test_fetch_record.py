"""GET /records/{id}: round-trips submitted data, org-scoped 404s."""
from __future__ import annotations


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _minimal_valid_payload() -> dict:
    return {
        "well": {
            "Well Specific": {
                "Well & Field Identification": {
                    "Well name": "FETCH-TEST",
                    "Well identification number": 42,
                }
            }
        },
        "production_intervals": [{"fields": {}, "completion_intervals": [{}]}],
    }


def test_fetch_round_trips_submitted_data(client, seeded_org):
    _, token = seeded_org
    submit_resp = client.post("/records", json=_minimal_valid_payload(), headers=_auth(token))
    record_id = submit_resp.json()["id"]

    fetch_resp = client.get(f"/records/{record_id}", headers=_auth(token))
    assert fetch_resp.status_code == 200
    body = fetch_resp.json()
    assert body["well"]["Well Specific"]["Well & Field Identification"]["Well name"] == "FETCH-TEST"
    assert len(body["production_intervals"]) == 1
    assert len(body["production_intervals"][0]["completion_intervals"]) == 1


def test_fetch_unknown_record_returns_404(client, seeded_org):
    _, token = seeded_org
    resp = client.get("/records/999999999", headers=_auth(token))
    assert resp.status_code == 404


def test_fetch_another_orgs_record_returns_404_not_403(client, db_session):
    from backend.app.deps.auth import hash_token
    from db.models import Organization

    org_a = Organization(name="Org A", slug="org-a-fetch-test", api_token_hash=hash_token("token-a-fetch-test"))
    org_b = Organization(name="Org B", slug="org-b-fetch-test", api_token_hash=hash_token("token-b-fetch-test"))
    db_session.add_all([org_a, org_b])
    db_session.flush()

    submit_resp = client.post("/records", json=_minimal_valid_payload(), headers=_auth("token-a-fetch-test"))
    record_id = submit_resp.json()["id"]

    fetch_resp = client.get(f"/records/{record_id}", headers=_auth("token-b-fetch-test"))
    assert fetch_resp.status_code == 404
