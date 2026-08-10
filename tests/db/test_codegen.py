"""Runs db.codegen against the real MASTER.xlsx and checks (a) it completes
without a naming collision or oversized identifier, and (b) what it
produces matches what's already committed under db/generated/ -- the same
drift check CI runs, so a dictionary edit that wasn't followed by
`python -m db.codegen` fails locally too, not just in CI.
"""
from __future__ import annotations

import json
from pathlib import Path

from db import codegen

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = REPO_ROOT / "db" / "generated"
GENERATED_FILES = [
    "well_columns.py",
    "production_interval_columns.py",
    "completion_interval_columns.py",
    "field_registry.json",
]


def test_codegen_runs_without_error():
    per_table = codegen.generate()
    assert set(per_table.keys()) == {"well", "production_interval", "completion_interval"}
    assert len(per_table["well"]) > 0
    assert len(per_table["completion_interval"]) > 0


def test_generated_output_matches_committed_files(tmp_path, monkeypatch):
    # Regenerate into a scratch directory rather than overwriting the real
    # db/generated/ as a side effect of running the test suite.
    monkeypatch.setattr(codegen, "GENERATED_DIR", tmp_path)
    codegen.generate()

    for name in GENERATED_FILES:
        committed = (GENERATED_DIR / name).read_text(encoding="utf-8")
        fresh = (tmp_path / name).read_text(encoding="utf-8")
        assert fresh == committed, f"{name} is stale -- run `python -m db.codegen` and commit the result"


def test_field_registry_has_one_entry_per_dictionary_row():
    from dictionary import load_dictionary

    registry = json.loads((GENERATED_DIR / "field_registry.json").read_text(encoding="utf-8"))
    rows = load_dictionary(codegen.MASTER_XLSX)
    assert len(registry) == len(rows)


def test_multi_number_fields_expand_to_multiple_columns():
    registry = json.loads((GENERATED_DIR / "field_registry.json").read_text(encoding="utf-8"))
    entry = registry["completion_interval::Drilling::Drilling Details::Mud PSD"]
    assert entry["db_columns"] == ["mud_psd_d10", "mud_psd_d50", "mud_psd_d90"]
    assert entry["db_type"] == "Numeric"
