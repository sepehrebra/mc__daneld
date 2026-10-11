from sqlalchemy import select

from app.reminders.service import process_due_reminders
from db import Reminder
from tests.test_crop_seasons import auth_headers, create_plot
from tests.test_operations import make_operation
from tests.test_reminders import create_reminder


def test_due_processing_is_bounded_idempotent_and_owner_scoped(registration_db) -> None:
    client, session_factory = registration_db
    owner = auth_headers(client, "09123456789")
    stranger = auth_headers(client, "09123456788")
    plot_id = create_plot(client, owner)
    operation = make_operation(client, owner, plot_id)
    assert operation.status_code == 201
    operation_id = operation.json()["id"]
    due_ids = []
    for remind_at in ("2026-10-15T07:59:00Z", "2026-10-15T08:00:00Z"):
        created = create_reminder(client, owner, operation_id, remind_at)
        assert created.status_code == 201
        due_ids.append(created.json()["id"])
    future = create_reminder(client, owner, operation_id, "2026-10-15T08:01:00Z")
    assert future.status_code == 201
    now = "2026-10-15T08:00:00.000000Z"
    with session_factory() as session:
        assert process_due_reminders(session, now=now, batch_size=1) == 1
        assert process_due_reminders(session, now=now, batch_size=1) == 1
        assert process_due_reminders(session, now=now, batch_size=1) == 0
        assert [session.scalar(select(Reminder).where(Reminder.id == reminder_id)).status for reminder_id in due_ids] == ["sent", "sent"]
        assert [session.scalar(select(Reminder).where(Reminder.id == reminder_id)).attempt_count for reminder_id in due_ids] == [1, 1]
        assert session.scalar(select(Reminder).where(Reminder.id == future.json()["id"])).status == "pending"

    notifications = client.get("/api/v1/notifications", headers=owner)
    assert notifications.status_code == 200
    assert len(notifications.json()) == 2
    assert {item["id"] for item in notifications.json()} == set(due_ids)
    assert all(item["operation_title"] == "Irrigate north plot" for item in notifications.json())
    assert all(item["read_at"] is None for item in notifications.json())
    assert client.get("/api/v1/notifications", headers=stranger).json() == []
    assert client.get("/api/v1/notifications").status_code == 401
    assert client.post(f"/api/v1/notifications/{due_ids[0]}/read", headers=stranger).status_code == 404
    assert client.post(f"/api/v1/notifications/{future.json()['id']}/read", headers=owner).status_code == 404

    read = client.post(f"/api/v1/notifications/{due_ids[0]}/read", headers=owner)
    assert read.status_code == 200
    assert read.json()["read_at"] is not None
    repeated = client.post(f"/api/v1/notifications/{due_ids[0]}/read", headers=owner)
    assert repeated.status_code == 200
    assert repeated.json()["read_at"] == read.json()["read_at"]
    unread = client.get("/api/v1/notifications", headers=owner, params={"unread_only": True})
    assert unread.status_code == 200
    assert [item["id"] for item in unread.json()] == [due_ids[1]]


def test_cancelled_reminders_are_not_published(registration_db) -> None:
    client, session_factory = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    operation = make_operation(client, headers, plot_id)
    assert operation.status_code == 201
    operation_id = operation.json()["id"]
    reminder = create_reminder(client, headers, operation_id, "2026-10-15T07:00:00Z")
    assert reminder.status_code == 201
    assert client.patch(
        f"/api/v1/operations/{operation_id}",
        headers=headers,
        json={"scheduled_date": "2026-10-16"},
    ).status_code == 200
    with session_factory() as session:
        assert process_due_reminders(session, now="2026-10-15T08:00:00.000000Z") == 0
    assert client.get("/api/v1/notifications", headers=headers).json() == []
    assert client.get(
        f"/api/v1/reminders/{reminder.json()['id']}", headers=headers
    ).json()["status"] == "cancelled"
