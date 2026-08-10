"""Base.metadata reflects the expected 4 tables with sane column counts and
correctly-wired foreign keys/cascades. Pure Python-object inspection --
does not need a live database.
"""
from __future__ import annotations

import db.models  # noqa: F401  (populates Base.metadata as a side effect)
from db.base import Base


def test_expected_tables_present():
    assert set(Base.metadata.tables.keys()) == {
        "organizations",
        "well",
        "production_interval",
        "completion_interval",
    }


def test_well_has_structural_plus_dictionary_columns():
    well = Base.metadata.tables["well"]
    structural = {"id", "organization_id", "created_at", "updated_at", "submitted_at", "raw_payload"}
    assert structural.issubset(set(well.columns.keys()))
    assert len(well.columns) > len(structural) + 50


def test_foreign_keys_wired_correctly():
    well = Base.metadata.tables["well"]
    production_interval = Base.metadata.tables["production_interval"]
    completion_interval = Base.metadata.tables["completion_interval"]

    assert {fk.target_fullname for fk in well.foreign_keys} == {"organizations.id"}
    assert {fk.target_fullname for fk in production_interval.foreign_keys} == {"well.id"}
    assert {fk.target_fullname for fk in completion_interval.foreign_keys} == {"production_interval.id"}


def test_cascade_delete_on_child_foreign_keys():
    production_interval = Base.metadata.tables["production_interval"]
    completion_interval = Base.metadata.tables["completion_interval"]
    (well_fk,) = production_interval.foreign_keys
    (pi_fk,) = completion_interval.foreign_keys
    assert well_fk.constraint.ondelete == "CASCADE"
    assert pi_fk.constraint.ondelete == "CASCADE"


def test_ordinal_unique_constraints_present():
    production_interval = Base.metadata.tables["production_interval"]
    completion_interval = Base.metadata.tables["completion_interval"]
    assert any(
        {c.name for c in uc.columns} == {"well_id", "ordinal"} for uc in production_interval.constraints
    )
    assert any(
        {c.name for c in uc.columns} == {"production_interval_id", "ordinal"} for uc in completion_interval.constraints
    )


def test_relationships_configure_without_error():
    from sqlalchemy.orm import configure_mappers

    configure_mappers()
