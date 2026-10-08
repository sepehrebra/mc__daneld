from sqlalchemy import update
from sqlalchemy.orm import Session

from db import Reminder


def cancel_active_reminders(session: Session, operation_id: str, now: str) -> None:
    session.execute(
        update(Reminder)
        .where(
            Reminder.operation_id == operation_id,
            Reminder.status.in_(("pending", "processing", "failed")),
        )
        .values(status="cancelled", updated_at=now)
    )
