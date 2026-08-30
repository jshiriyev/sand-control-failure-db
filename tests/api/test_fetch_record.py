"""GET /records/{id}: round-trips submitted data, org-scoped 404s."""
from __future__ import annotations


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_fetch_round_trips_submitted_data(client, seeded_org, make_payload):
    _, token = seeded_org
    payload = make_payload()
    payload["well"]["Well Specific"]["Well & Field Identification"]["Well name (anonymized)"] = "FETCHTEST"
    submit_resp = client.post("/records", json=payload, headers=_auth(token))
    assert submit_resp.status_code == 201, submit_resp.text
    record_id = submit_resp.json()["id"]

    fetch_resp = client.get(f"/records/{record_id}", headers=_auth(token))
    assert fetch_resp.status_code == 200
    body = fetch_resp.json()
    ident = body["well"]["Well Specific"]["Well & Field Identification"]
    assert ident["Well name (anonymized)"] == "FETCHTEST"
    assert len(body["completion_intervals"]) == 1
    assert len(body["completion_intervals"][0]["sand_bodies"]) == 1


def test_fetch_unknown_record_returns_404(client, seeded_org):
    _, token = seeded_org
    resp = client.get("/records/999999999", headers=_auth(token))
    assert resp.status_code == 404


def test_fetch_another_orgs_record_returns_404_not_403(client, db_session, make_payload):
    from backend.app.deps.auth import hash_token
    from db.models import Organization

    org_a = Organization(name="Org A", slug="org-a-fetch-test", api_token_hash=hash_token("token-a-fetch-test"))
    org_b = Organization(name="Org B", slug="org-b-fetch-test", api_token_hash=hash_token("token-b-fetch-test"))
    db_session.add_all([org_a, org_b])
    db_session.flush()

    submit_resp = client.post("/records", json=make_payload(), headers=_auth("token-a-fetch-test"))
    assert submit_resp.status_code == 201, submit_resp.text
    record_id = submit_resp.json()["id"]

    fetch_resp = client.get(f"/records/{record_id}", headers=_auth("token-b-fetch-test"))
    assert fetch_resp.status_code == 404
