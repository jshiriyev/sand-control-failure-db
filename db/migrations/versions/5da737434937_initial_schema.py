"""initial schema

Creates the 4 baseline tables (organizations, well, production_interval,
completion_interval) as they originally existed, before the later
"restructure well -> completion_interval -> sand_body hierarchy" migration
(ce34a815d3e9) replaced production_interval/completion_interval with
completion_interval/sand_body.

This uses explicit op.create_table() calls with literal column lists rather
than delegating to Base.metadata.create_all() against the live db.models --
that was this migration's original approach (see git history), justified at
the time by not having a live Postgres available to diff against, but
Base.metadata is a shared, mutable, *current* registry: once db.models
itself changed shape for ce34a815d3e9, create_all() silently started
building the *new* shape here too, skipping the old shape entirely and
making ce34a815d3e9's own DROP TABLE calls fail against dependents that
should not have existed yet. Migrations must be frozen historical records,
not live reflections of whatever the current models say -- this file is
rewritten to actually be that.

Revision ID: 5da737434937
Revises:
Create Date: 2026-08-09 21:32:24.811699

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5da737434937'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("api_token_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("api_token_hash"),
    )
    op.create_table(
        "well",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("data_source", sa.Text(), nullable=True, comment="Data source"),
        sa.Column("data_confidence_level", sa.Text(), nullable=True, comment="Data confidence level"),
        sa.Column("disclosure_level", sa.Text(), nullable=True, comment="Disclosure level"),
        sa.Column("notes_comments", sa.Text(), nullable=True, comment="Notes / comments"),
        sa.Column("well_name", sa.Text(), nullable=True, comment="Well name"),
        sa.Column("well_identification_number", sa.Integer(), nullable=True, comment="Well identification number"),
        sa.Column("well_type", sa.Text(), nullable=True, comment="Well type"),
        sa.Column("operating_environment", sa.Text(), nullable=True, comment="Operating environment"),
        sa.Column("water_depth", sa.Numeric(), nullable=True, comment="Water depth"),
        sa.Column("tree_type", sa.Text(), nullable=True, comment="Tree type"),
        sa.Column("well_td_md", sa.Numeric(), nullable=True, comment="Well TD, MD"),
        sa.Column("well_td_tvd_rkb", sa.Numeric(), nullable=True, comment="Well TD, TVD (RKB)"),
        sa.Column("field_name", sa.Text(), nullable=True, comment="Field name"),
        sa.Column("operator_name", sa.Text(), nullable=True, comment="Operator name"),
        sa.Column("operator_type", sa.Text(), nullable=True, comment="Operator type"),
        sa.Column("region", sa.Text(), nullable=True, comment="Region"),
        sa.Column("sand_failure", sa.Boolean(), nullable=True, comment="Sand failure"),
        sa.Column("severity_of_sand_production", sa.Text(), nullable=True, comment="Severity of sand production"),
        sa.Column("time_to_first_choke_back", sa.Numeric(), nullable=True, comment="Time to first choke back"),
        sa.Column("time_to_well_shut_in_due_to_sand", sa.Numeric(), nullable=True, comment="Time to well shut-in due to sand"),
        sa.Column("time_to_complete_well_failure", sa.Numeric(), nullable=True, comment="Time to complete well failure"),
        sa.Column("how_is_sand_production_known", sa.Text(), nullable=True, comment="How is sand production known?"),
        sa.Column("sand_failure_mechanism", sa.Text(), nullable=True, comment="Sand failure mechanism"),
        sa.Column("severity_of_sand_control_failure", sa.Text(), nullable=True, comment="Severity of sand control failure"),
        sa.Column("sand_production_rate_at_first_choke_back", sa.Numeric(), nullable=True, comment="Sand production rate at first choke back"),
        sa.Column("sand_production_rate_at_well_shut_in_due_to_sand", sa.Numeric(), nullable=True, comment="Sand production rate at well shut-in due to sand"),
        sa.Column("sand_production_rate_at_complete_well_failure", sa.Numeric(), nullable=True, comment="Sand production rate at complete well failure"),
        sa.Column("initial_pi", sa.Numeric(), nullable=True, comment="Initial PI"),
        sa.Column("initial_total_skin", sa.Numeric(), nullable=True, comment="Initial total skin"),
        sa.Column("initial_non_darcy_skin", sa.Numeric(), nullable=True, comment="Initial non-Darcy skin"),
        sa.Column("initial_deviated_well_skin", sa.Numeric(), nullable=True, comment="Initial deviated well skin"),
        sa.Column("well_pi_after_choke_back", sa.Numeric(), nullable=True, comment="Well PI after choke-back"),
        sa.Column("total_skin_after_choke_back", sa.Numeric(), nullable=True, comment="Total skin after choke-back"),
        sa.Column("non_darcy_skin_after_choke_back", sa.Numeric(), nullable=True, comment="Non-Darcy skin after choke-back"),
        sa.Column("deviated_well_skin_after_choke_back", sa.Numeric(), nullable=True, comment="Deviated well skin after choke-back"),
        sa.Column("lessons_learned_classification_rcfa_outcomes", sa.Text(), nullable=True, comment="Lessons learned classification / RCFA outcomes"),
        sa.Column("current_well_status", sa.Text(), nullable=True, comment="Current well status"),
        sa.Column("well_start_up_date", sa.Date(), nullable=True, comment="Well start-up date"),
        sa.Column("first_production_date", sa.Date(), nullable=True, comment="First production date"),
        sa.Column("last_production_date", sa.Date(), nullable=True, comment="Last production date"),
        sa.Column("oil_rate_the_first_choke_back", sa.Numeric(), nullable=True, comment="Oil Rate @ The First Choke Back"),
        sa.Column("oil_rate_shut_in", sa.Numeric(), nullable=True, comment="Oil Rate @ Shut-in"),
        sa.Column("gas_rate_the_first_choke_back", sa.Numeric(), nullable=True, comment="Gas Rate @ The First Choke Back"),
        sa.Column("gas_rate_shut_in", sa.Numeric(), nullable=True, comment="Gas Rate @ Shut-in"),
        sa.Column("water_rate_the_first_choke_back", sa.Numeric(), nullable=True, comment="Water Rate @ The First Choke Back"),
        sa.Column("water_rate_shut_in", sa.Numeric(), nullable=True, comment="Water Rate @ Shut-in"),
        sa.Column("peak_oil_rate", sa.Numeric(), nullable=True, comment="Peak oil rate"),
        sa.Column("peak_gas_rate", sa.Numeric(), nullable=True, comment="Peak gas rate"),
        sa.Column("peak_water_rate", sa.Numeric(), nullable=True, comment="Peak water rate"),
        sa.Column("peak_water_cut", sa.Numeric(), nullable=True, comment="Peak water cut"),
        sa.Column("sand_rate_quantification", sa.Text(), nullable=True, comment="Sand rate quantification"),
        sa.Column("max_sand_rate", sa.Numeric(), nullable=True, comment="Max sand rate"),
        sa.Column("average_sand_rate", sa.Numeric(), nullable=True, comment="Average sand rate"),
        sa.Column("known_sand_face_production_chemistry_issues", sa.Text(), nullable=True, comment="Known sand face production chemistry issues"),
        sa.Column("initial_reservoir_pore_pressure", sa.Numeric(), nullable=True, comment="Initial reservoir pore pressure"),
        sa.Column("max_drawdown_over_well_life", sa.Numeric(), nullable=True, comment="Max drawdown over well life"),
        sa.Column("p50_drawdown_over_well_life", sa.Numeric(), nullable=True, comment="P50 drawdown over well life"),
        sa.Column("typical_post_shut_in_bean_up_strategy", sa.Text(), nullable=True, comment="Typical post-shut-in bean-up strategy"),
        sa.Column("post_shut_in_oil_gas_production_rate_response", sa.Text(), nullable=True, comment="Post shut-in oil/gas production rate response"),
        sa.Column("post_shut_in_water_cut_response", sa.Text(), nullable=True, comment="Post-shut-in water-cut response"),
        sa.Column("post_shut_in_sand_response", sa.Text(), nullable=True, comment="Post-shut-in sand response"),
        sa.Column("number_of_production_intervals", sa.Integer(), nullable=True, comment="Number of production intervals"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
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


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("completion_interval")
    op.drop_table("production_interval")
    op.drop_table("well")
    op.drop_table("organizations")
