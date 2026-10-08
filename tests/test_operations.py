from datetime import datetime, timezone

from sqlalchemy import select

from db import Operation
from tests.test_crop_seasons import auth_headers, create_plot


def make_operation(client, headers, plot_id, **changes):
    payload = {
        "title": "Irrigate north plot",
        "operation_type": "irrigation",
        "scheduled_date": "2026-10-15",
    }
    payload.update(changes)
    return client.post(f"/api/v1/plots/{plot_id}/operations", headers=headers, json=payload)


def test_create_and_read_operation_with_crop_season(registration_db) -> None:
    client, session_factory = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    season = client.post(
        f"/api/v1/plots/{plot_id}/crop-seasons",
        headers=headers,
        json={"crop_name": "Wheat", "start_date": "2026-10-01"},
    )
    assert season.status_code == 201
    season_id = season.json()["id"]
    created = make_operation(
        client,
        headers,
        plot_id,
        title="  Water wheat  ",
        crop_season_id=season_id,
        scheduled_time="08:30:00",
        description="First irrigation",
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Water wheat"
    assert body["plot_id"] == plot_id
    assert body["crop_season_id"] == season_id
    assert body["scheduled_time"] == "08:30:00"
    assert body["status"] == "planned"
    assert body["completed_at"] is None
    assert body["result_notes"] is None
    assert body["created_at"] == body["updated_at"]
    assert client.get(f"/api/v1/operations/{body['id']}", headers=headers).json() == body
    assert client.get(f"/api/v1/plots/{plot_id}/operations", headers=headers).json() == [body]
    assert client.get("/api/v1/operations", headers=headers).json() == [body]
    assert client.delete(f"/api/v1/crop-seasons/{season_id}", headers=headers).status_code == 409
    assert client.delete(f"/api/v1/plots/{plot_id}", headers=headers).status_code == 409
    with session_factory() as session:
        stored = session.scalar(select(Operation).where(Operation.id == body["id"]))
        assert stored is not None
        assert stored.created_by == body["created_by"]


def test_invalid_payload_and_cross_plot_season_are_rejected(registration_db) -> None:
    client, _ = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    other_plot_id = create_plot(client, headers)
    season = client.post(
        f"/api/v1/plots/{other_plot_id}/crop-seasons",
        headers=headers,
        json={"crop_name": "Barley", "start_date": "2026-10-01"},
    )
    assert season.status_code == 201
    assert make_operation(client, headers, plot_id, crop_season_id=season.json()["id"]).status_code == 422
    for changes in (
        {"scheduled_date": "2026-02-29"},
        {"scheduled_date": "2026-1-01"},
        {"scheduled_date": None},
        {"scheduled_time": "24:00:00"},
        {"scheduled_time": "08:30"},
        {"operation_type": "unknown"},
        {"title": "   "},
        {"created_by": season.json()["id"]},
        {"status": "completed"},
        {"completed_at": "2026-10-15T08:30:00Z"},
    ):
        assert make_operation(client, headers, plot_id, **changes).status_code == 422
    assert make_operation(client, headers, plot_id).status_code == 201


def test_list_filters_are_inclusive_and_owner_scoped(registration_db) -> None:
    client, _ = registration_db
    owner = auth_headers(client, "09123456789")
    stranger = auth_headers(client, "09123456788")
    plot_id = create_plot(client, owner)
    second_plot_id = create_plot(client, owner)
    ids = []
    for date in ("2026-10-14", "2026-10-15", "2026-10-16"):
        response = make_operation(client, owner, plot_id, scheduled_date=date)
        assert response.status_code == 201
        ids.append(response.json()["id"])
    second = make_operation(client, owner, second_plot_id, scheduled_date="2026-10-15")
    assert second.status_code == 201
    stranger_plot = create_plot(client, stranger)
    assert make_operation(client, stranger, stranger_plot).status_code == 201
    filtered = client.get(
        "/api/v1/operations",
        headers=owner,
        params={"plot_id": plot_id, "date_from": "2026-10-15", "date_to": "2026-10-16"},
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == ids[1:]
    assert len(client.get("/api/v1/operations", headers=owner).json()) == 4
    assert len(client.get("/api/v1/operations", headers=stranger).json()) == 1
    assert client.get(
        f"/api/v1/plots/{plot_id}/operations", headers=owner,
        params={"date_from": "2026-10-15", "date_to": "2026-10-15"},
    ).json()[0]["id"] == ids[1]
    for params in (
        {"date_from": "2026-10-16", "date_to": "2026-10-15"},
        {"date_from": "2026-02-29"},
        {"date_to": "2026-1-01"},
    ):
        assert client.get("/api/v1/operations", headers=owner, params=params).status_code == 422
    assert client.post(f"/api/v1/plots/{plot_id}/operations", json={}).status_code == 401
    assert make_operation(client, stranger, plot_id).status_code == 404
    assert client.get(f"/api/v1/operations/{ids[0]}", headers=stranger).status_code == 404
    assert client.get(f"/api/v1/plots/{plot_id}/operations", headers=stranger).status_code == 404
    assert client.get("/api/v1/operations", headers=stranger, params={"plot_id": plot_id}).status_code == 404


def test_reschedule_start_and_complete_records_actual_utc_time(registration_db) -> None:
    client, session_factory = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    created = make_operation(client, headers, plot_id, scheduled_time="08:30:00")
    assert created.status_code == 201
    operation_id = created.json()["id"]
    path = f"/api/v1/operations/{operation_id}"

    rescheduled = client.patch(
        path, headers=headers,
        json={"scheduled_date": "2026-10-16", "scheduled_time": None},
    )
    assert rescheduled.status_code == 200
    assert rescheduled.json()["scheduled_date"] == "2026-10-16"
    assert rescheduled.json()["scheduled_time"] is None
    assert rescheduled.json()["status"] == "planned"
    assert rescheduled.json()["completed_at"] is None
    assert client.get("/api/v1/operations", headers=headers, params={"date_from": "2026-10-16"}).json()[0]["id"] == operation_id

    started = client.patch(path, headers=headers, json={"status": "in_progress"})
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert started.json()["completed_at"] is None
    before = datetime.now(timezone.utc)
    completed = client.patch(
        path, headers=headers,
        json={"status": "completed", "result_notes": "Watering completed"},
    )
    after = datetime.now(timezone.utc)
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "completed"
    assert body["result_notes"] == "Watering completed"
    actual = datetime.strptime(body["completed_at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    assert before <= actual <= after
    assert body["updated_at"] == body["completed_at"]
    assert body["scheduled_date"] == "2026-10-16"
    with session_factory() as session:
        stored = session.scalar(select(Operation).where(Operation.id == operation_id))
        assert stored is not None and stored.completed_at == body["completed_at"]

    repeated = client.patch(path, headers=headers, json={"status": "completed"})
    assert repeated.status_code == 200
    assert repeated.json()["completed_at"] == body["completed_at"]
    corrected = client.patch(path, headers=headers, json={"result_notes": "Done"})
    assert corrected.status_code == 200
    assert corrected.json()["result_notes"] == "Done"
    assert corrected.json()["completed_at"] == body["completed_at"]


def test_cancel_and_direct_completion_and_invalid_transitions(registration_db) -> None:
    client, _ = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    first = make_operation(client, headers, plot_id)
    second = make_operation(client, headers, plot_id)
    assert first.status_code == second.status_code == 201
    first_path = f"/api/v1/operations/{first.json()['id']}"
    second_path = f"/api/v1/operations/{second.json()['id']}"

    cancelled = client.patch(first_path, headers=headers, json={"status": "cancelled"})
    assert cancelled.status_code == 200
    assert cancelled.json()["completed_at"] is None
    assert client.patch(first_path, headers=headers, json={"status": "in_progress"}).status_code == 409
    assert client.patch(first_path, headers=headers, json={"scheduled_date": "2026-10-17"}).status_code == 409
    assert client.patch(first_path, headers=headers, json={"result_notes": "No"}).status_code == 422

    completed = client.patch(second_path, headers=headers, json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None
    assert client.patch(second_path, headers=headers, json={"status": "cancelled"}).status_code == 409
    assert client.patch(second_path, headers=headers, json={"scheduled_time": None}).status_code == 409
    assert client.patch(second_path, headers=headers, json={"completed_at": None}).status_code == 422


def test_update_validation_and_owner_scope(registration_db) -> None:
    client, _ = registration_db
    owner = auth_headers(client, "09123456789")
    stranger = auth_headers(client, "09123456788")
    plot_id = create_plot(client, owner)
    created = make_operation(client, owner, plot_id)
    assert created.status_code == 201
    path = f"/api/v1/operations/{created.json()['id']}"
    assert client.patch(path, json={"status": "completed"}).status_code == 401
    assert client.patch(path, headers=stranger, json={"status": "completed"}).status_code == 404
    for payload in (
        {"scheduled_date": None},
        {"scheduled_date": "2026-02-29"},
        {"scheduled_time": "24:00:00"},
        {"status": None},
        {"status": "unknown"},
        {"result_notes": "premature"},
        {"created_by": created.json()["created_by"]},
        {"plot_id": plot_id},
    ):
        assert client.patch(path, headers=owner, json=payload).status_code == 422
    assert client.get(path, headers=owner).json()["status"] == "planned"
    assert client.patch(path, headers=owner, json={"status": "in_progress"}).status_code == 200
    assert client.patch(path, headers=owner, json={"status": "planned"}).status_code == 409
