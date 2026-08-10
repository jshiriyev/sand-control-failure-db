"""Org-token bearer auth: missing/malformed/unknown token -> 401; valid
token passes through to the route (a 404 for a nonexistent record proves
auth itself succeeded).
"""
from __future__ import annotations


def test_missing_authorization_header(client):
    resp = client.get("/records/1")
    assert resp.status_code == 401


def test_malformed_authorization_header(client):
    resp = client.get("/records/1", headers={"Authorization": "Basic xxx"})
    assert resp.status_code == 401


def test_unknown_token(client):
    resp = client.get("/records/1", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_valid_token_passes_auth(client, seeded_org):
    _, token = seeded_org
    resp = client.get("/records/999999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404  # auth passed; the record itself doesn't exist
