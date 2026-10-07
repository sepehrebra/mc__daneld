"""Create operations linked to plots, crop seasons, and users.

Revision ID: 0006_create_operations
Revises: 0005_create_crop_seasons
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_create_operations"
down_revision: Union[str, Sequence[str], None] = "0005_create_crop_seasons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("plot_id", sa.Text(), nullable=False),
        sa.Column("crop_season_id", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheduled_date", sa.Text(), nullable=False),
        sa.Column("scheduled_time", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="planned"),
        sa.Column("result_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["plot_id"], ["plots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["crop_season_id"], ["crop_seasons.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "operation_type IN ('planting', 'irrigation', 'fertilizing', "
            "'spraying', 'harvesting', 'other')",
            name="ck_operations_type",
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
            name="ck_operations_status",
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR "
            "(status != 'completed' AND completed_at IS NULL)",
            name="ck_operations_completion_time",
        ),
    )
    op.create_index("ix_operations_plot_date", "operations", ["plot_id", "scheduled_date"])
    op.create_index("ix_operations_crop_season_id", "operations", ["crop_season_id"])
    op.create_index("ix_operations_created_by", "operations", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_operations_created_by", table_name="operations")
    op.drop_index("ix_operations_crop_season_id", table_name="operations")
    op.drop_index("ix_operations_plot_date", table_name="operations")
    op.drop_table("operations")
