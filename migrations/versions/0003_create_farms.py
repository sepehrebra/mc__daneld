"""Create farms owned by users.

Revision ID: 0003_create_farms
Revises: 0002_create_auth_sessions
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_create_farms"
down_revision: Union[str, Sequence[str], None] = "0002_create_auth_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farms",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("province", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="Asia/Tehran"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_farms_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_farms_longitude"),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_farms_coordinates_pair",
        ),
    )
    op.create_index("ix_farms_owner_id", "farms", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_farms_owner_id", table_name="farms")
    op.drop_table("farms")
