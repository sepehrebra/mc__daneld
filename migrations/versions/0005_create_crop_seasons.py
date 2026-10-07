"""Create crop seasons linked to plots.

Revision ID: 0005_create_crop_seasons
Revises: 0004_create_plots
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_create_crop_seasons"
down_revision: Union[str, Sequence[str], None] = "0004_create_plots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crop_seasons",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("plot_id", sa.Text(), nullable=False),
        sa.Column("crop_name", sa.Text(), nullable=False),
        sa.Column("variety", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Text(), nullable=False),
        sa.Column("actual_start_date", sa.Text(), nullable=True),
        sa.Column("expected_end_date", sa.Text(), nullable=True),
        sa.Column("actual_end_date", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="planned"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["plot_id"], ["plots.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_crop_seasons_status",
        ),
    )
    op.create_index("ix_crop_seasons_plot_id", "crop_seasons", ["plot_id"])


def downgrade() -> None:
    op.drop_index("ix_crop_seasons_plot_id", table_name="crop_seasons")
    op.drop_table("crop_seasons")
