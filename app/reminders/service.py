from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import Operation, Reminder, utc_now


def cancel_active_reminders(session: Session, operation_id: str, now: str) -> None:
    session.execute(
        update(Reminder)
        .where(
            Reminder.operation_id == operation_id,
            Reminder.status.in_(("pending", "processing", "failed")),
        )
        .values(status="cancelled", updated_at=now)
    )


def process_due_reminders(
    session: Session, *, now: str | None = None, batch_size: int = 100
) -> int:
    """Publish a bounded batch of in-app notifications exactly once in SQLite."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")
    current_time = now or utc_now()
    due_ids = (
        select(Reminder.id)
        .join(Operation, Reminder.operation_id == Operation.id)
        .where(
            Reminder.status == "pending",
            Reminder.remind_at <= current_time,
            Operation.status.in_(("planned", "in_progress")),
        )
        .order_by(Reminder.remind_at, Reminder.id)
        .limit(batch_size)
    )
    sent_ids = list(
        session.scalars(
            update(Reminder)
            .where(Reminder.id.in_(due_ids), Reminder.status == "pending")
            .values(
                status="sent",
                sent_at=current_time,
                updated_at=current_time,
                attempt_count=Reminder.attempt_count + 1,
            )
            .returning(Reminder.id)
        )
    )
    session.commit()
    return len(sent_ids)
