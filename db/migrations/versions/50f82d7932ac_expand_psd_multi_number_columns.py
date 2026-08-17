"""expand PSD multi-number columns to D-labeled sub-fields

MASTER.xlsx's "Mud PSD" (completion_interval scope) and "Particle Size
Distribution D10/D25/D40/D50/D75/D90" (sand_body scope) Parameters were
edited to resolve the two "Known open items" noted in CLAUDE.md: Mud PSD's
Parameter name now carries a trailing "D10/D25/D40/D50/D75/D90" suffix
(previously fell back to generic mud_psd_value_1/2/3), and the sand_body
Parameter was renamed "PSD D10/D25/D40/D50/D75/D90" (previously
particle_size_distribution_value_1..5, which was itself already a
generic-label fallback due to a Data Validation cell missing its 6th
entry). Both now expand to 6 D-labeled columns via the normal
dictionary.parsing._derive_multi_labels path. No live Postgres was
available to autogenerate this against, so it's hand-authored -- same
constraint as the two migrations before it.

Revision ID: 50f82d7932ac
Revises: ce34a815d3e9
Create Date: 2026-08-16 23:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '50f82d7932ac'
down_revision: Union[str, Sequence[str], None] = 'ce34a815d3e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("completion_interval", "mud_psd_value_1")
    op.drop_column("completion_interval", "mud_psd_value_2")
    op.drop_column("completion_interval", "mud_psd_value_3")
    op.add_column("completion_interval", sa.Column("mud_psd_d10", sa.Numeric(), nullable=True, comment="Mud PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("completion_interval", sa.Column("mud_psd_d25", sa.Numeric(), nullable=True, comment="Mud PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("completion_interval", sa.Column("mud_psd_d40", sa.Numeric(), nullable=True, comment="Mud PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("completion_interval", sa.Column("mud_psd_d50", sa.Numeric(), nullable=True, comment="Mud PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("completion_interval", sa.Column("mud_psd_d75", sa.Numeric(), nullable=True, comment="Mud PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("completion_interval", sa.Column("mud_psd_d90", sa.Numeric(), nullable=True, comment="Mud PSD D10/D25/D40/D50/D75/D90"))

    op.drop_column("sand_body", "particle_size_distribution_value_1")
    op.drop_column("sand_body", "particle_size_distribution_value_2")
    op.drop_column("sand_body", "particle_size_distribution_value_3")
    op.drop_column("sand_body", "particle_size_distribution_value_4")
    op.drop_column("sand_body", "particle_size_distribution_value_5")
    op.add_column("sand_body", sa.Column("psd_d10", sa.Numeric(), nullable=True, comment="PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("psd_d25", sa.Numeric(), nullable=True, comment="PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("psd_d40", sa.Numeric(), nullable=True, comment="PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("psd_d50", sa.Numeric(), nullable=True, comment="PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("psd_d75", sa.Numeric(), nullable=True, comment="PSD D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("psd_d90", sa.Numeric(), nullable=True, comment="PSD D10/D25/D40/D50/D75/D90"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sand_body", "psd_d90")
    op.drop_column("sand_body", "psd_d75")
    op.drop_column("sand_body", "psd_d50")
    op.drop_column("sand_body", "psd_d40")
    op.drop_column("sand_body", "psd_d25")
    op.drop_column("sand_body", "psd_d10")
    op.add_column("sand_body", sa.Column("particle_size_distribution_value_5", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("particle_size_distribution_value_4", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("particle_size_distribution_value_3", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("particle_size_distribution_value_2", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"))
    op.add_column("sand_body", sa.Column("particle_size_distribution_value_1", sa.Numeric(), nullable=True, comment="Particle Size Distribution D10/D25/D40/D50/D75/D90"))

    op.drop_column("completion_interval", "mud_psd_d90")
    op.drop_column("completion_interval", "mud_psd_d75")
    op.drop_column("completion_interval", "mud_psd_d50")
    op.drop_column("completion_interval", "mud_psd_d40")
    op.drop_column("completion_interval", "mud_psd_d25")
    op.drop_column("completion_interval", "mud_psd_d10")
    op.add_column("completion_interval", sa.Column("mud_psd_value_3", sa.Numeric(), nullable=True, comment="Mud PSD"))
    op.add_column("completion_interval", sa.Column("mud_psd_value_2", sa.Numeric(), nullable=True, comment="Mud PSD"))
    op.add_column("completion_interval", sa.Column("mud_psd_value_1", sa.Numeric(), nullable=True, comment="Mud PSD"))
