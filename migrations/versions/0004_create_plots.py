"""Create plots linked to farms.

Revision ID: 0004_create_plots
Revises: 0003_create_farms
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_create_plots"
down_revision: Union[str, Sequence[str], None] = "0003_create_farms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plots",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("farm_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("area_m2", sa.REAL(), nullable=False),
        sa.Column("soil_type", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("farm_id", "name", name="uq_plots_farm_name"),
        sa.UniqueConstraint("farm_id", "code", name="uq_plots_farm_code"),
        sa.CheckConstraint("area_m2 > 0", name="ck_plots_area_positive"),
    )
    op.create_index("ix_plots_farm_id", "plots", ["farm_id"])


def downgrade() -> None:
    op.drop_index("ix_plots_farm_id", table_name="plots")
    op.drop_table("plots")
