from sqlalchemy import select

from db import Reminder
from tests.test_crop_seasons import auth_headers, create_plot
from tests.test_operations import make_operation


def create_reminder(client, headers, operation_id, remind_at="2026-10-15T08:00:00Z"):
    return client.post(
        f"/api/v1/operations/{operation_id}/reminders",
        headers=headers,
        json={"remind_at": remind_at},
    )


def test_create_list_get_and_cancel_reminder(registration_db) -> None:
    client, session_factory = registration_db
    owner = auth_headers(client, "09123456789")
    stranger = auth_headers(client, "09123456788")
    plot_id = create_plot(client, owner)
    operation = make_operation(client, owner, plot_id)
    assert operation.status_code == 201
    operation_id = operation.json()["id"]
    created = create_reminder(client, owner, operation_id, "2026-10-15T11:30:00+03:30")
    assert created.status_code == 201
    body = created.json()
    reminder_id = body["id"]
    assert body["operation_id"] == operation_id
    assert body["recipient_id"] == operation.json()["created_by"]
    assert body["remind_at"] == "2026-10-15T08:00:00.000000Z"
    assert body["channel"] == "in_app"
    assert body["status"] == "pending"
    assert body["attempt_count"] == 0
    assert body["sent_at"] is None
    assert body["read_at"] is None
    assert "last_error" not in body
    assert client.get(f"/api/v1/reminders/{reminder_id}", headers=owner).json() == body
    assert client.get(f"/api/v1/operations/{operation_id}/reminders", headers=owner).json() == [body]
    with session_factory() as session:
        stored = session.scalar(select(Reminder).where(Reminder.id == reminder_id))
        assert stored is not None and stored.remind_at == body["remind_at"]

    assert client.get(f"/api/v1/reminders/{reminder_id}", headers=stranger).status_code == 404
    assert client.get(f"/api/v1/operations/{operation_id}/reminders", headers=stranger).status_code == 404
    assert create_reminder(client, stranger, operation_id).status_code == 404
    assert client.post(f"/api/v1/reminders/{reminder_id}/cancel", headers=stranger).status_code == 404
    assert client.get(f"/api/v1/reminders/{reminder_id}").status_code == 401

    cancelled = client.post(f"/api/v1/reminders/{reminder_id}/cancel", headers=owner)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    repeated = client.post(f"/api/v1/reminders/{reminder_id}/cancel", headers=owner)
    assert repeated.status_code == 200
    assert repeated.json() == cancelled.json()


def test_reminder_input_and_finished_operation_restrictions(registration_db) -> None:
    client, session_factory = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    operation = make_operation(client, headers, plot_id)
    assert operation.status_code == 201
    operation_id = operation.json()["id"]
    path = f"/api/v1/operations/{operation_id}/reminders"
    for payload in (
        {},
        {"remind_at": "2026-10-15T08:00:00"},
        {"remind_at": "2026-02-29T08:00:00Z"},
        {"remind_at": "2026-10-15 08:00:00Z"},
        {"remind_at": "2026-10-15T25:00:00Z"},
        {"remind_at": None},
        {"remind_at": "2026-10-15T08:00:00Z", "recipient_id": operation.json()["created_by"]},
        {"remind_at": "2026-10-15T08:00:00Z", "status": "sent"},
    ):
        assert client.post(path, headers=headers, json=payload).status_code == 422
    assert client.get(path, headers=headers).json() == []
    reminder = create_reminder(client, headers, operation_id)
    assert reminder.status_code == 201
    reminder_id = reminder.json()["id"]
    with session_factory() as session:
        stored = session.scalar(select(Reminder).where(Reminder.id == reminder_id))
        stored.status = "sent"
        session.commit()
    assert client.post(f"/api/v1/reminders/{reminder_id}/cancel", headers=headers).status_code == 409
    assert client.patch(
        f"/api/v1/operations/{operation_id}", headers=headers, json={"status": "completed"}
    ).status_code == 200
    assert create_reminder(client, headers, operation_id).status_code == 409


def test_rescheduling_and_finishing_cancel_old_reminders(registration_db) -> None:
    client, _ = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    operation = make_operation(client, headers, plot_id, scheduled_time="09:00:00")
    assert operation.status_code == 201
    operation_id = operation.json()["id"]
    operation_path = f"/api/v1/operations/{operation_id}"
    first = create_reminder(client, headers, operation_id)
    second = create_reminder(client, headers, operation_id, "2026-10-15T07:00:00Z")
    assert first.status_code == second.status_code == 201

    same = client.patch(operation_path, headers=headers, json={"scheduled_time": "09:00:00"})
    assert same.status_code == 200
    assert [item["status"] for item in client.get(
        f"{operation_path}/reminders", headers=headers
    ).json()] == ["pending", "pending"]
    changed = client.patch(operation_path, headers=headers, json={"scheduled_time": "10:00:00"})
    assert changed.status_code == 200
    assert [item["status"] for item in client.get(
        f"{operation_path}/reminders", headers=headers
    ).json()] == ["cancelled", "cancelled"]
    replacement = create_reminder(client, headers, operation_id, "2026-10-15T08:30:00Z")
    assert replacement.status_code == 201
    assert replacement.json()["status"] == "pending"
    started = client.patch(operation_path, headers=headers, json={"status": "in_progress"})
    assert started.status_code == 200
    assert client.get(f"/api/v1/reminders/{replacement.json()['id']}", headers=headers).json()["status"] == "pending"
    completed = client.patch(operation_path, headers=headers, json={"status": "completed"})
    assert completed.status_code == 200
    assert client.get(f"/api/v1/reminders/{replacement.json()['id']}", headers=headers).json()["status"] == "cancelled"

    other = make_operation(client, headers, plot_id)
    assert other.status_code == 201
    other_id = other.json()["id"]
    other_reminder = create_reminder(client, headers, other_id)
    assert other_reminder.status_code == 201
    assert client.patch(
        f"/api/v1/operations/{other_id}", headers=headers, json={"status": "cancelled"}
    ).status_code == 200
    assert client.get(
        f"/api/v1/reminders/{other_reminder.json()['id']}", headers=headers
    ).json()["status"] == "cancelled"
