"""restructure well -> completion_interval -> sand_body hierarchy

MASTER.xlsx's Scope hierarchy changed from
    Well -> Production Interval {id} -> Completion Interval {id}
to
    Well -> Completion Interval {id} -> Sand Body {id}

i.e. the former "Production Interval" level is now called "Completion
Interval" (and gained the drilling/completion/sand-control-equipment columns
that used to live one level down), and the former "Completion Interval"
level (sand bodies) is now its own "Sand Body" level holding the
per-sand-body pre-production/cleanup and reservoir-characterization columns.
This is a genuine restructuring, not a rename Alembic autogenerate could
detect on its own -- both the parent/child relationships and the column
sets attached to each level changed, so this migration was hand-authored:
drop the two old-shape tables, adjust `well`'s two affected columns, and
create the two new-shape tables. See CLAUDE.md's "Scope hierarchy" section.

There is no production data in any environment this migration will run
against yet (see CLAUDE.md's "Path to production" -- the project isn't
onboarding real companies), so this drops and recreates rather than
attempting an in-place data migration.

Revision ID: ce34a815d3e9
Revises: 5da737434937
Create Date: 2026-08-12 22:47:00.649519

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ce34a815d3e9'
down_revision: Union[str, Sequence[str], None] = '5da737434937'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Old shape: well -> production_interval -> completion_interval (sand bodies).
    # completion_interval (old) must drop before production_interval (its FK parent).
    op.drop_table("completion_interval")
    op.drop_table("production_interval")

    op.drop_column("well", "number_of_production_intervals")
    op.add_column("well", sa.Column("number_of_completion_intervals", sa.Integer(), nullable=True, comment="Number of Completion Intervals"))

    # New shape: well -> completion_interval -> sand_body.
    op.create_table(
        "completion_interval",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("well_id", sa.Integer(), nullable=False, index=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completion_interval_length", sa.Numeric(), nullable=True, comment="Completion Interval Length"),
        sa.Column("drill_bit_size", sa.Numeric(), nullable=True, comment="Drill Bit Size"),
        sa.Column("reservoir_drilling_fluid_type", sa.Text(), nullable=True, comment="Reservoir Drilling Fluid Type"),
        sa.Column("reservoir_drilling_fluid_density", sa.Numeric(), nullable=True, comment="Reservoir Drilling Fluid Density"),
        sa.Column("weighting_agent", sa.Text(), nullable=True, comment="Weighting Agent"),
        sa.Column("additional_bridging_agent", sa.Text(), nullable=True, comment="Additional Bridging Agent"),
        sa.Column("mud_psd_value_1", sa.Numeric(), nullable=True, comment="Mud PSD"),
        sa.Column("mud_psd_value_2", sa.Numeric(), nullable=True, comment="Mud PSD"),
        sa.Column("mud_psd_value_3", sa.Numeric(), nullable=True, comment="Mud PSD"),
        sa.Column("psd_test_volume", sa.Numeric(), nullable=True, comment="PSD Test Volume"),
        sa.Column("completion_type", sa.Text(), nullable=True, comment="Completion Type"),
        sa.Column("sandface_completion_date", sa.Date(), nullable=True, comment="Sandface Completion Date"),
        sa.Column("hole_size", sa.Numeric(), nullable=True, comment="Hole Size"),
        sa.Column("gross_open_hole_length", sa.Numeric(), nullable=True, comment="Gross Open Hole Length"),
        sa.Column("net_pay_length", sa.Numeric(), nullable=True, comment="Net Pay Length"),
        sa.Column("fluid_type_left_in_oh_at_end_of_completion", sa.Text(), nullable=True, comment="Fluid Type Left in OH at end of Completion"),
        sa.Column("casing_size", sa.Numeric(), nullable=True, comment="Casing Size"),
        sa.Column("gross_perf_length", sa.Numeric(), nullable=True, comment="Gross Perf Length"),
        sa.Column("net_perf_length", sa.Numeric(), nullable=True, comment="Net Perf Length"),
        sa.Column("perforation_gun_size", sa.Numeric(), nullable=True, comment="Perforation Gun Size"),
        sa.Column("perforation_spf", sa.Numeric(), nullable=True, comment="Perforation SPF"),
        sa.Column("perforation_charge_casing_material", sa.Text(), nullable=True, comment="Perforation Charge Casing Material"),
        sa.Column("charge_type", sa.Text(), nullable=True, comment="Charge Type"),
        sa.Column("perforation_strategy", sa.Text(), nullable=True, comment="Perforation Strategy"),
        sa.Column("ob_ob_magnitude", sa.Numeric(), nullable=True, comment="OB / OB Magnitude"),
        sa.Column("open_hole_sand_control_selected_method", sa.Text(), nullable=True, comment="Open Hole Sand Control Selected Method"),
        sa.Column("cased_hole_sand_control_selected_method", sa.Text(), nullable=True, comment="Cased Hole Sand Control Selected Method"),
        sa.Column("sand_control_decision_justification", sa.Text(), nullable=True, comment="Sand Control Decision Justification"),
        sa.Column("screen_type", sa.Text(), nullable=True, comment="Screen Type"),
        sa.Column("icd_aicd", sa.Boolean(), nullable=True, comment="ICD / AICD"),
        sa.Column("screen_gauge", sa.Numeric(), nullable=True, comment="Screen Gauge"),
        sa.Column("screen_base_pipe_size", sa.Numeric(), nullable=True, comment="Screen Base Pipe Size"),
        sa.Column("screen_rih_fluid_type", sa.Text(), nullable=True, comment="Screen RIH Fluid Type"),
        sa.Column("if_screens_ran_in_mud_was_mud_removed_once_screens_on_bottom", sa.Boolean(), nullable=True, comment="If screens ran in mud, was mud removed once screens on bottom?"),
        sa.Column("filter_cake_breaker_placement", sa.Text(), nullable=True, comment="Filter cake breaker placement"),
        sa.Column("placement_method", sa.Text(), nullable=True, comment="Placement Method"),
        sa.Column("proppant_type", sa.Text(), nullable=True, comment="Proppant Type"),
        sa.Column("proppant_size", sa.Numeric(), nullable=True, comment="Proppant Size"),
        sa.Column("proppant_unit_length", sa.Numeric(), nullable=True, comment="Proppant / Unit Length"),
        sa.Column("carrier_fluid_type", sa.Text(), nullable=True, comment="Carrier Fluid Type"),
        sa.Column("carrier_fluid_density", sa.Numeric(), nullable=True, comment="Carrier Fluid Density"),
        sa.Column("max_proppant_concentration", sa.Numeric(), nullable=True, comment="Max Proppant Concentration"),
        sa.Column("max_pump_rate", sa.Numeric(), nullable=True, comment="Max Pump Rate"),
        sa.Column("net_pressure_gain", sa.Numeric(), nullable=True, comment="Net Pressure Gain"),
        sa.Column("return_percentage", sa.Numeric(), nullable=True, comment="Return Percentage"),
        sa.Column("pack_efficiency_source", sa.Text(), nullable=True, comment="Pack Efficiency Source"),
        sa.Column("pack_efficiency_value", sa.Numeric(), nullable=True, comment="Pack Efficiency Value"),
        sa.Column("placement_issues", sa.Text(), nullable=True, comment="Placement Issues"),
        sa.Column("number_of_sand_bodies", sa.Integer(), nullable=True, comment="Number of sand bodies"),
        sa.ForeignKeyConstraint(["well_id"], ["well.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("well_id", "ordinal", name="uq_completion_interval_well_ordinal"),
    )
    op.create_table(
        "sand_body",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("completion_interval_id", sa.Integer(), nullable=False, index=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("remedial_acid_pumped_as_productivity_was_below_expectation", sa.Text(), nullable=True, comment="Remedial Acid Pumped as Productivity was Below Expectation"),
        sa.Column("remedial_acid_helped_productivity", sa.Text(), nullable=True, comment="Remedial Acid Helped Productivity"),
        sa.Column("remedial_acid_type", sa.Text(), nullable=True, comment="Remedial Acid Type"),
        sa.Column("percentage_of_ideal_pi_or_skin_achieved", sa.Integer(), nullable=True, comment="Percentage of ideal PI or skin achieved"),
        sa.Column("virgin_reservoir_pressure", sa.Numeric(), nullable=True, comment="Virgin Reservoir Pressure"),
        sa.Column("reservoir_pressure_at_time_of_completion", sa.Numeric(), nullable=True, comment="Reservoir Pressure at Time of Completion"),
        sa.Column("reservoir_pressure_at_first_sand_production", sa.Numeric(), nullable=True, comment="Reservoir pressure at first sand production"),
        sa.Column("reservoir_temperature", sa.Numeric(), nullable=True, comment="Reservoir Temperature"),
        sa.Column("core_derived_min_rock_ucs", sa.Numeric(), nullable=True, comment="Core Derived Min Rock UCS"),
        sa.Column("core_derived_p50_rock_ucs", sa.Numeric(), nullable=True, comment="Core Derived P50 Rock UCS"),
        sa.Column("shale_reactivity_cec", sa.Numeric(), nullable=True, comment="Shale Reactivity CEC"),
        sa.Column("rock_compressibility_at_initial_reservoir_pressure", sa.Numeric(), nullable=True, comment="Rock compressibility at initial reservoir pressure"),
        sa.Column("rock_compressibility_at_first_sand_production", sa.Numeric(), nullable=True, comment="Rock compressibility at first sand production"),
        sa.Column("source_of_sand_sample", sa.Text(), nullable=True, comment="Source of sand sample"),
        sa.Column("psd_measurement_method", sa.Text(), nullable=True, comment="PSD Measurement Method"),
        sa.Column("particle_size_distribution_value_1", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_value_2", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_value_3", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_value_4", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_value_5", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("fines_content", sa.Numeric(), nullable=True, comment="Fines Content"),
        sa.Column("initial_pi", sa.Numeric(), nullable=True, comment="Initial PI"),
        sa.Column("porosity", sa.Numeric(), nullable=True, comment="Porosity"),
        sa.Column("permeability", sa.Numeric(), nullable=True, comment="Permeability"),
        sa.Column("k_h_from_pta", sa.Numeric(), nullable=True, comment="k.h from PTA"),
        sa.Column("k_h_from_log", sa.Numeric(), nullable=True, comment="k.h from Log"),
        sa.Column("initial_total_skin_from_pta", sa.Integer(), nullable=True, comment="Initial Total Skin from PTA"),
        sa.Column("fluid_type", sa.Text(), nullable=True, comment="Fluid Type"),
        sa.Column("oil_formation_volume_factor_bo_at_downhole_conditions", sa.Numeric(), nullable=True, comment="Oil Formation Volume Factor (Bo) at downhole conditions"),
        sa.Column("producing_fluid_viscosity", sa.Numeric(), nullable=True, comment="Producing Fluid Viscosity"),
        sa.Column("oil_bubble_point_pb", sa.Numeric(), nullable=True, comment="Oil Bubble Point (Pb)"),
        sa.Column("solution_gas_ratio_rs", sa.Numeric(), nullable=True, comment="Solution Gas Ratio (Rs)"),
        sa.Column("frac_gradient", sa.Numeric(), nullable=True, comment="Frac gradient"),
        sa.ForeignKeyConstraint(["completion_interval_id"], ["completion_interval.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("completion_interval_id", "ordinal", name="uq_sand_body_ci_ordinal"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # New shape must drop child-first.
    op.drop_table("sand_body")
    op.drop_table("completion_interval")

    op.drop_column("well", "number_of_completion_intervals")
    op.add_column("well", sa.Column("number_of_production_intervals", sa.Integer(), nullable=True, comment="Number of production intervals"))

    # Old shape: well -> production_interval -> completion_interval (sand bodies).
    op.create_table(
        "production_interval",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("well_id", sa.Integer(), nullable=False, index=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("number_of_completion_intervals", sa.Integer(), nullable=True, comment="Number of Completion Intervals"),
        sa.ForeignKeyConstraint(["well_id"], ["well.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("well_id", "ordinal", name="uq_production_interval_well_ordinal"),
    )
    op.create_table(
        "completion_interval",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("production_interval_id", sa.Integer(), nullable=False, index=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completion_interval_length", sa.Numeric(), nullable=True, comment="Completion Interval Length"),
        sa.Column("drill_bit_size", sa.Numeric(), nullable=True, comment="Drill Bit Size"),
        sa.Column("reservoir_drilling_fluid_type", sa.Text(), nullable=True, comment="Reservoir Drilling Fluid Type"),
        sa.Column("reservoir_drilling_fluid_density", sa.Numeric(), nullable=True, comment="Reservoir Drilling Fluid Density"),
        sa.Column("weighting_agent", sa.Text(), nullable=True, comment="Weighting Agent"),
        sa.Column("additional_bridging_agent", sa.Text(), nullable=True, comment="Additional Bridging Agent"),
        sa.Column("mud_psd_d10", sa.Numeric(), nullable=True, comment="Mud PSD"),
        sa.Column("mud_psd_d50", sa.Numeric(), nullable=True, comment="Mud PSD"),
        sa.Column("mud_psd_d90", sa.Numeric(), nullable=True, comment="Mud PSD"),
        sa.Column("psd_test_volume", sa.Numeric(), nullable=True, comment="PSD Test Volume"),
        sa.Column("completion_type", sa.Text(), nullable=True, comment="Completion Type"),
        sa.Column("sandface_completion_date", sa.Date(), nullable=True, comment="Sandface Completion Date"),
        sa.Column("hole_size", sa.Numeric(), nullable=True, comment="Hole Size"),
        sa.Column("gross_open_hole_length", sa.Numeric(), nullable=True, comment="Gross Open Hole Length"),
        sa.Column("net_pay_length", sa.Numeric(), nullable=True, comment="Net Pay Length"),
        sa.Column("fluid_type_left_in_oh_at_end_of_completion", sa.Text(), nullable=True, comment="Fluid Type Left in OH at end of Completion"),
        sa.Column("casing_size", sa.Numeric(), nullable=True, comment="Casing Size"),
        sa.Column("gross_perf_length", sa.Numeric(), nullable=True, comment="Gross Perf Length"),
        sa.Column("net_perf_length", sa.Numeric(), nullable=True, comment="Net Perf Length"),
        sa.Column("perforation_gun_size", sa.Numeric(), nullable=True, comment="Perforation Gun Size"),
        sa.Column("perforation_spf", sa.Numeric(), nullable=True, comment="Perforation SPF"),
        sa.Column("perforation_charge_casing_material", sa.Text(), nullable=True, comment="Perforation Charge Casing Material"),
        sa.Column("charge_type", sa.Text(), nullable=True, comment="Charge Type"),
        sa.Column("perforation_strategy", sa.Text(), nullable=True, comment="Perforation Strategy"),
        sa.Column("ob_ob_magnitude", sa.Numeric(), nullable=True, comment="OB / OB Magnitude"),
        sa.Column("open_hole_sand_control_selected_method", sa.Text(), nullable=True, comment="Open Hole Sand Control Selected Method"),
        sa.Column("cased_hole_sand_control_selected_method", sa.Text(), nullable=True, comment="Cased Hole Sand Control Selected Method"),
        sa.Column("sand_control_decision_justification", sa.Text(), nullable=True, comment="Sand Control Decision Justification"),
        sa.Column("screen_type", sa.Text(), nullable=True, comment="Screen Type"),
        sa.Column("icd_aicd", sa.Boolean(), nullable=True, comment="ICD / AICD"),
        sa.Column("screen_gauge", sa.Numeric(), nullable=True, comment="Screen Gauge"),
        sa.Column("screen_base_pipe_size", sa.Numeric(), nullable=True, comment="Screen Base Pipe Size"),
        sa.Column("screen_rih_fluid_type", sa.Text(), nullable=True, comment="Screen RIH Fluid Type"),
        sa.Column("if_screens_ran_in_mud_was_mud_removed_once_screens_on_bottom", sa.Boolean(), nullable=True, comment="If screens ran in mud, was mud removed once screens on bottom?"),
        sa.Column("filter_cake_breaker_placement", sa.Text(), nullable=True, comment="Filter cake breaker placement"),
        sa.Column("placement_method", sa.Text(), nullable=True, comment="Placement Method"),
        sa.Column("proppant_type", sa.Text(), nullable=True, comment="Proppant Type"),
        sa.Column("proppant_size", sa.Numeric(), nullable=True, comment="Proppant Size"),
        sa.Column("proppant_unit_length", sa.Numeric(), nullable=True, comment="Proppant / Unit Length"),
        sa.Column("carrier_fluid_type", sa.Text(), nullable=True, comment="Carrier Fluid Type"),
        sa.Column("carrier_fluid_density", sa.Numeric(), nullable=True, comment="Carrier Fluid Density"),
        sa.Column("max_proppant_concentration", sa.Numeric(), nullable=True, comment="Max Proppant Concentration"),
        sa.Column("max_pump_rate", sa.Numeric(), nullable=True, comment="Max Pump Rate"),
        sa.Column("net_pressure_gain", sa.Numeric(), nullable=True, comment="Net Pressure Gain"),
        sa.Column("return_percentage", sa.Numeric(), nullable=True, comment="Return Percentage"),
        sa.Column("pack_efficiency_source", sa.Text(), nullable=True, comment="Pack Efficiency Source"),
        sa.Column("pack_efficiency_value", sa.Numeric(), nullable=True, comment="Pack Efficiency Value"),
        sa.Column("placement_issues", sa.Text(), nullable=True, comment="Placement Issues"),
        sa.Column("remedial_acid_pumped_as_productivity_was_below_expectation", sa.Text(), nullable=True, comment="Remedial Acid Pumped as Productivity was Below Expectation"),
        sa.Column("remedial_acid_helped_productivity", sa.Text(), nullable=True, comment="Remedial Acid Helped Productivity"),
        sa.Column("remedial_acid_type", sa.Text(), nullable=True, comment="Remedial Acid Type"),
        sa.Column("percentage_of_ideal_pi_or_skin_achieved", sa.Numeric(), nullable=True, comment="Percentage of ideal PI or skin achieved"),
        sa.Column("virgin_reservoir_pressure", sa.Numeric(), nullable=True, comment="Virgin Reservoir Pressure"),
        sa.Column("reservoir_pressure_at_time_of_completion", sa.Numeric(), nullable=True, comment="Reservoir Pressure at Time of Completion"),
        sa.Column("reservoir_pressure_at_first_sand_production", sa.Numeric(), nullable=True, comment="Reservoir pressure at first sand production"),
        sa.Column("reservoir_temperature", sa.Numeric(), nullable=True, comment="Reservoir Temperature"),
        sa.Column("core_derived_min_rock_ucs", sa.Numeric(), nullable=True, comment="Core Derived Min Rock UCS"),
        sa.Column("core_derived_p50_rock_ucs", sa.Numeric(), nullable=True, comment="Core Derived P50 Rock UCS"),
        sa.Column("shale_reactivity_cec", sa.Numeric(), nullable=True, comment="Shale Reactivity CEC"),
        sa.Column("rock_compressibility_at_initial_reservoir_pressure", sa.Numeric(), nullable=True, comment="Rock compressibility at initial reservoir pressure"),
        sa.Column("rock_compressibility_at_first_sand_production", sa.Numeric(), nullable=True, comment="Rock compressibility at first sand production"),
        sa.Column("source_of_sand_sample", sa.Text(), nullable=True, comment="Source of sand sample"),
        sa.Column("psd_measurement_method", sa.Text(), nullable=True, comment="PSD Measurement Method"),
        sa.Column("particle_size_distribution_d10", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_d25", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_d40", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_d50", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_d75", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("particle_size_distribution_d90", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"),
        sa.Column("fines_content", sa.Numeric(), nullable=True, comment="Fines Content"),
        sa.Column("initial_pi", sa.Numeric(), nullable=True, comment="Initial PI"),
        sa.Column("porosity", sa.Numeric(), nullable=True, comment="Porosity"),
        sa.Column("permeability", sa.Numeric(), nullable=True, comment="Permeability"),
        sa.Column("k_h_from_pta", sa.Numeric(), nullable=True, comment="k.h from PTA"),
        sa.Column("k_h_from_log", sa.Numeric(), nullable=True, comment="k.h from Log"),
        sa.Column("initial_total_skin_from_pta", sa.Numeric(), nullable=True, comment="Initial Total Skin from PTA"),
        sa.Column("fluid_type", sa.Text(), nullable=True, comment="Fluid Type"),
        sa.Column("oil_formation_volume_factor_bo_at_downhole_conditions", sa.Numeric(), nullable=True, comment="Oil Formation Volume Factor (Bo) at downhole conditions"),
        sa.Column("producing_fluid_viscosity", sa.Numeric(), nullable=True, comment="Producing Fluid Viscosity"),
        sa.Column("oil_bubble_point_pb", sa.Numeric(), nullable=True, comment="Oil Bubble Point (Pb)"),
        sa.Column("solution_gas_ratio_rs", sa.Numeric(), nullable=True, comment="Solution Gas Ratio (Rs)"),
        sa.Column("frac_gradient", sa.Numeric(), nullable=True, comment="Frac gradient"),
        sa.ForeignKeyConstraint(["production_interval_id"], ["production_interval.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_interval_id", "ordinal", name="uq_completion_interval_pi_ordinal"),
    )
