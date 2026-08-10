"""db.naming: no collisions, valid Postgres identifiers, correct
multi-number suffixing."""
from __future__ import annotations

import pytest

from db.naming import MAX_IDENTIFIER_LENGTH, derive_column_names, slugify, strip_multi_suffix


def test_slugify_basic():
    assert slugify("Data source") == "data_source"


def test_slugify_punctuation_and_commas():
    assert slugify("Well TD, MD") == "well_td_md"
    assert slugify("k.h from PTA") == "k_h_from_pta"
    assert slugify("ICD / AICD") == "icd_aicd"


def test_slugify_empty_result_raises():
    with pytest.raises(ValueError):
        slugify("???")


def test_strip_multi_suffix_removes_trailing_slash_run():
    assert strip_multi_suffix("Particle Size Distribution D10/D25/D40/D50/D75/D90") == "Particle Size Distribution"


def test_strip_multi_suffix_no_suffix_present_is_a_no_op():
    assert strip_multi_suffix("Mud PSD") == "Mud PSD"


def test_derive_column_names_plain_field():
    assert derive_column_names("Water depth", "number", []) == ["water_depth"]


def test_derive_column_names_multi_number_from_unit_labels():
    names = derive_column_names("Mud PSD", "multi_number", ["D10", "D50", "D90"])
    assert names == ["mud_psd_d10", "mud_psd_d50", "mud_psd_d90"]


def test_derive_column_names_multi_number_from_parameter_suffix():
    names = derive_column_names(
        "Particle Size Distribution D10/D25/D40/D50/D75/D90",
        "multi_number",
        ["D10", "D25", "D40", "D50", "D75", "D90"],
    )
    assert names == [
        "particle_size_distribution_d10",
        "particle_size_distribution_d25",
        "particle_size_distribution_d40",
        "particle_size_distribution_d50",
        "particle_size_distribution_d75",
        "particle_size_distribution_d90",
    ]


def test_derive_column_names_rejects_overlong_identifier():
    with pytest.raises(ValueError):
        derive_column_names("x " * 40, "text", [])


def test_max_identifier_length_matches_postgres_limit():
    assert MAX_IDENTIFIER_LENGTH == 63
