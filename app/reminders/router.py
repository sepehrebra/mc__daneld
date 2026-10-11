from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.operations.router import owned_operation
from app.reminders.schemas import NotificationPublic, ReminderCreate, ReminderPublic
from app.users.auth import AuthContext, require_auth
from db import Farm, Operation, Plot, Reminder, get_db, utc_now

router = APIRouter(prefix="/api/v1", tags=["reminders"])


def owned_reminder(reminder_id: UUID, owner_id: str, session: Session) -> Reminder:
    reminder = session.scalar(
        select(Reminder)
        .join(Operation, Reminder.operation_id == Operation.id)
        .join(Plot, Operation.plot_id == Plot.id)
        .join(Farm, Plot.farm_id == Farm.id)
        .where(
            Reminder.id == str(reminder_id),
            Reminder.recipient_id == owner_id,
            Farm.owner_id == owner_id,
        )
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return reminder


@router.post("/operations/{operation_id}/reminders", response_model=ReminderPublic, status_code=201)
def create_reminder(
    operation_id: UUID,
    payload: ReminderCreate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Reminder:
    operation = owned_operation(operation_id, auth.user.id, session)
    if operation.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Finished operations cannot have new reminders.")
    now = utc_now()
    reminder = Reminder(
        operation_id=operation.id,
        recipient_id=auth.user.id,
        remind_at=payload.remind_at,
        channel="in_app",
        status="pending",
        attempt_count=0,
        created_at=now,
        updated_at=now,
    )
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return reminder


@router.get("/operations/{operation_id}/reminders", response_model=list[ReminderPublic])
def list_operation_reminders(
    operation_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> list[Reminder]:
    operation = owned_operation(operation_id, auth.user.id, session)
    return list(
        session.scalars(
            select(Reminder)
            .where(Reminder.operation_id == operation.id, Reminder.recipient_id == auth.user.id)
            .order_by(Reminder.remind_at, Reminder.id)
        )
    )


@router.get("/reminders/{reminder_id}", response_model=ReminderPublic)
def get_reminder(
    reminder_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Reminder:
    return owned_reminder(reminder_id, auth.user.id, session)


@router.post("/reminders/{reminder_id}/cancel", response_model=ReminderPublic)
def cancel_reminder(
    reminder_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Reminder:
    reminder = owned_reminder(reminder_id, auth.user.id, session)
    if reminder.status == "cancelled":
        return reminder
    if reminder.status == "sent":
        raise HTTPException(status_code=409, detail="Sent reminders cannot be cancelled.")
    reminder.status = "cancelled"
    reminder.updated_at = utc_now()
    session.commit()
    session.refresh(reminder)
    return reminder


@router.get("/notifications", response_model=list[NotificationPublic])
def list_notifications(
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
    unread_only: bool = False,
) -> list[NotificationPublic]:
    query = (
        select(Reminder, Operation.title)
        .join(Operation, Reminder.operation_id == Operation.id)
        .join(Plot, Operation.plot_id == Plot.id)
        .join(Farm, Plot.farm_id == Farm.id)
        .where(
            Reminder.recipient_id == auth.user.id,
            Farm.owner_id == auth.user.id,
            Reminder.status == "sent",
        )
    )
    if unread_only:
        query = query.where(Reminder.read_at.is_(None))
    rows = session.execute(query.order_by(Reminder.sent_at.desc(), Reminder.id)).all()
    return [
        NotificationPublic(
            id=reminder.id,
            operation_id=reminder.operation_id,
            operation_title=title,
            remind_at=reminder.remind_at,
            sent_at=reminder.sent_at,
            read_at=reminder.read_at,
        )
        for reminder, title in rows
    ]


@router.post("/notifications/{reminder_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    reminder_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> NotificationPublic:
    reminder = owned_reminder(reminder_id, auth.user.id, session)
    if reminder.status != "sent":
        raise HTTPException(status_code=404, detail="Notification not found.")
    if reminder.read_at is None:
        reminder.read_at = utc_now()
        reminder.updated_at = reminder.read_at
        session.commit()
        session.refresh(reminder)
    title = session.scalar(select(Operation.title).where(Operation.id == reminder.operation_id))
    return NotificationPublic(
        id=reminder.id,
        operation_id=reminder.operation_id,
        operation_title=title,
        remind_at=reminder.remind_at,
        sent_at=reminder.sent_at,
        read_at=reminder.read_at,
    )
