"""sync well and completion_interval columns with the latest MASTER.xlsx

Covers the round of SME-feedback edits to MASTER.xlsx made since the last
schema migration (50f82d7932ac): 21 Parameters added, 13 removed (including
old un-split versions of renamed/split Parameters -- e.g. "Open Hole Sand
Control Selected Method"/"Cased Hole Sand Control Selected Method" were
replaced by "OH ..."/"CH ..." with different Parameter text, so codegen's
Parameter-name-derived column slugs treat them as distinct columns, not a
rename), and 3 Input Type changes (Filter cake breaker placement, Placement
Issues: Dropdown Menu -> Boolean; Proppant Size: Number -> Dropdown Menu).
"Well name"/"Well identification number" were replaced by anonymized
variants ("... (anonymized)"), the latter also switching from a plain
Integer to a length/pattern-constrained Text column. No production data
exists yet in any environment this runs against (see CLAUDE.md's "Path to
production"), so type changes are handled as drop+add rather than an
in-place ALTER COLUMN ... USING cast, consistent with the two migrations
before this one. No live Postgres was available to autogenerate this
against, so -- same as every migration so far -- it's hand-authored:
derived from a column-by-column diff between `db/generated/*_columns.py`
(regenerated from the current MASTER.xlsx) and the schema reconstructed
from replaying 5da737434937 -> ce34a815d3e9 -> 50f82d7932ac. `sand_body`
is unaffected by this round of edits.

Revision ID: f04e20471f4a
Revises: 50f82d7932ac
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f04e20471f4a'
down_revision: Union[str, Sequence[str], None] = '50f82d7932ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- well ---
    op.drop_column("well", "average_sand_rate")
    op.drop_column("well", "disclosure_level")
    op.drop_column("well", "initial_reservoir_pore_pressure")
    op.drop_column("well", "max_sand_rate")
    op.drop_column("well", "severity_of_sand_control_failure")
    op.drop_column("well", "severity_of_sand_production")
    op.drop_column("well", "well_identification_number")
    op.drop_column("well", "well_name")
    op.add_column("well", sa.Column("severity_of_sand_production_gas_well", sa.Text(), nullable=True, comment="Severity of sand production - Gas Well"))
    op.add_column("well", sa.Column("severity_of_sand_production_oil_well", sa.Text(), nullable=True, comment="Severity of sand production - Oil Well"))
    op.add_column("well", sa.Column("well_identification_number_anonymized", sa.Text(), nullable=True, comment="Well identification number (anonymized)"))
    op.add_column("well", sa.Column("well_name_anonymized", sa.Text(), nullable=True, comment="Well name (anonymized)"))

    # --- completion_interval ---
    op.drop_column("completion_interval", "carrier_fluid_type")
    op.drop_column("completion_interval", "cased_hole_sand_control_selected_method")
    op.drop_column("completion_interval", "open_hole_sand_control_selected_method")
    op.drop_column("completion_interval", "pack_efficiency_value")
    op.drop_column("completion_interval", "screen_rih_fluid_type")
    op.drop_column("completion_interval", "filter_cake_breaker_placement")
    op.drop_column("completion_interval", "placement_issues")
    op.drop_column("completion_interval", "proppant_size")
    op.add_column("completion_interval", sa.Column("filter_cake_breaker_placement", sa.Boolean(), nullable=True, comment="Filter cake breaker placement"))
    op.add_column("completion_interval", sa.Column("placement_issues", sa.Boolean(), nullable=True, comment="Placement Issues"))
    op.add_column("completion_interval", sa.Column("proppant_size", sa.Text(), nullable=True, comment="Proppant Size"))
    op.add_column("completion_interval", sa.Column("blank_pipe_run_across_non_pay_sections_instead_of_screens", sa.Boolean(), nullable=True, comment="Blank pipe run across non-pay sections instead of screens?"))
    op.add_column("completion_interval", sa.Column("carrier_fluid_type_chfp", sa.Text(), nullable=True, comment="Carrier Fluid Type - CHFP"))
    op.add_column("completion_interval", sa.Column("carrier_fluid_type_chgp", sa.Text(), nullable=True, comment="Carrier Fluid Type - CHGP"))
    op.add_column("completion_interval", sa.Column("carrier_fluid_type_ohgp", sa.Text(), nullable=True, comment="Carrier Fluid Type - OHGP"))
    op.add_column("completion_interval", sa.Column("casing_size_above_oh", sa.Numeric(), nullable=True, comment="Casing Size above OH"))
    op.add_column("completion_interval", sa.Column("ch_sand_control_selected_method", sa.Text(), nullable=True, comment="CH Sand Control Selected Method"))
    op.add_column("completion_interval", sa.Column("did_screens_get_to_target_setting_depth", sa.Boolean(), nullable=True, comment="Did screens get to Target Setting Depth"))
    op.add_column("completion_interval", sa.Column("filter_media_size", sa.Numeric(), nullable=True, comment="Filter Media Size"))
    op.add_column("completion_interval", sa.Column("full_pack_from_log", sa.Boolean(), nullable=True, comment="Full Pack from Log"))
    op.add_column("completion_interval", sa.Column("oh_sand_control_selected_method", sa.Text(), nullable=True, comment="OH Sand Control Selected Method"))
    op.add_column("completion_interval", sa.Column("open_hole_packers_deployed", sa.Boolean(), nullable=True, comment="Open Hole Packers deployed"))
    op.add_column("completion_interval", sa.Column("pack_efficiency_percentage", sa.Numeric(), nullable=True, comment="Pack Efficiency Percentage"))
    op.add_column("completion_interval", sa.Column("pack_through_shunts", sa.Numeric(), nullable=True, comment="% Pack through Shunts"))
    op.add_column("completion_interval", sa.Column("perf_packing", sa.Numeric(), nullable=True, comment="Perf Packing"))
    op.add_column("completion_interval", sa.Column("screen_rih_fluid_type_in_casing", sa.Text(), nullable=True, comment="Screen RIH Fluid Type in Casing"))
    op.add_column("completion_interval", sa.Column("screen_rih_fluid_type_in_open_hole", sa.Text(), nullable=True, comment="Screen RIH Fluid Type in Open-Hole"))
    op.add_column("completion_interval", sa.Column("shunt_tubes", sa.Boolean(), nullable=True, comment="Shunt Tubes"))


def downgrade() -> None:
    """Downgrade schema."""
    # --- completion_interval ---
    op.drop_column("completion_interval", "shunt_tubes")
    op.drop_column("completion_interval", "screen_rih_fluid_type_in_open_hole")
    op.drop_column("completion_interval", "screen_rih_fluid_type_in_casing")
    op.drop_column("completion_interval", "perf_packing")
    op.drop_column("completion_interval", "pack_through_shunts")
    op.drop_column("completion_interval", "pack_efficiency_percentage")
    op.drop_column("completion_interval", "open_hole_packers_deployed")
    op.drop_column("completion_interval", "oh_sand_control_selected_method")
    op.drop_column("completion_interval", "full_pack_from_log")
    op.drop_column("completion_interval", "filter_media_size")
    op.drop_column("completion_interval", "did_screens_get_to_target_setting_depth")
    op.drop_column("completion_interval", "ch_sand_control_selected_method")
    op.drop_column("completion_interval", "casing_size_above_oh")
    op.drop_column("completion_interval", "carrier_fluid_type_ohgp")
    op.drop_column("completion_interval", "carrier_fluid_type_chgp")
    op.drop_column("completion_interval", "carrier_fluid_type_chfp")
    op.drop_column("completion_interval", "blank_pipe_run_across_non_pay_sections_instead_of_screens")
    op.drop_column("completion_interval", "proppant_size")
    op.drop_column("completion_interval", "placement_issues")
    op.drop_column("completion_interval", "filter_cake_breaker_placement")
    op.add_column("completion_interval", sa.Column("proppant_size", sa.Numeric(), nullable=True, comment="Proppant Size"))
    op.add_column("completion_interval", sa.Column("placement_issues", sa.Text(), nullable=True, comment="Placement Issues"))
    op.add_column("completion_interval", sa.Column("filter_cake_breaker_placement", sa.Text(), nullable=True, comment="Filter cake breaker placement"))
    op.add_column("completion_interval", sa.Column("screen_rih_fluid_type", sa.Text(), nullable=True, comment="Screen RIH Fluid Type"))
    op.add_column("completion_interval", sa.Column("pack_efficiency_value", sa.Numeric(), nullable=True, comment="Pack Efficiency Value"))
    op.add_column("completion_interval", sa.Column("open_hole_sand_control_selected_method", sa.Text(), nullable=True, comment="Open Hole Sand Control Selected Method"))
    op.add_column("completion_interval", sa.Column("cased_hole_sand_control_selected_method", sa.Text(), nullable=True, comment="Cased Hole Sand Control Selected Method"))
    op.add_column("completion_interval", sa.Column("carrier_fluid_type", sa.Text(), nullable=True, comment="Carrier Fluid Type"))

    # --- well ---
    op.drop_column("well", "well_name_anonymized")
    op.drop_column("well", "well_identification_number_anonymized")
    op.drop_column("well", "severity_of_sand_production_oil_well")
    op.drop_column("well", "severity_of_sand_production_gas_well")
    op.add_column("well", sa.Column("well_name", sa.Text(), nullable=True, comment="Well name"))
    op.add_column("well", sa.Column("well_identification_number", sa.Integer(), nullable=True, comment="Well identification number"))
    op.add_column("well", sa.Column("severity_of_sand_production", sa.Text(), nullable=True, comment="Severity of sand production"))
    op.add_column("well", sa.Column("severity_of_sand_control_failure", sa.Text(), nullable=True, comment="Severity of sand control failure"))
    op.add_column("well", sa.Column("max_sand_rate", sa.Numeric(), nullable=True, comment="Max sand rate"))
    op.add_column("well", sa.Column("initial_reservoir_pore_pressure", sa.Numeric(), nullable=True, comment="Initial reservoir pore pressure"))
    op.add_column("well", sa.Column("disclosure_level", sa.Text(), nullable=True, comment="Disclosure level"))
    op.add_column("well", sa.Column("average_sand_rate", sa.Numeric(), nullable=True, comment="Average sand rate"))
