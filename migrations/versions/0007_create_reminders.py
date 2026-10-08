"""Create in-app reminders for operations.

Revision ID: 0007_create_reminders
Revises: 0006_create_operations
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_create_reminders"
down_revision: Union[str, Sequence[str], None] = "0006_create_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.Text(), nullable=False),
        sa.Column("recipient_id", sa.Text(), nullable=False),
        sa.Column("remind_at", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False, server_default="in_app"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.Text(), nullable=True),
        sa.Column("read_at", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("channel = 'in_app'", name="ck_reminders_channel"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed', 'cancelled')",
            name="ck_reminders_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_reminders_attempt_count"),
    )
    op.create_index("ix_reminders_operation_id", "reminders", ["operation_id"])
    op.create_index(
        "ix_reminders_recipient_status_due",
        "reminders",
        ["recipient_id", "status", "remind_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_reminders_recipient_status_due", table_name="reminders")
    op.drop_index("ix_reminders_operation_id", table_name="reminders")
    op.drop_table("reminders")
