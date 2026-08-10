"""GET /health -- needs a real Postgres (see tests/conftest.py), since it
round-trips a real query rather than just checking the process is alive.
"""
from __future__ import annotations


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
