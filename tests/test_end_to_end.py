from app.reminders.service import process_due_reminders


def test_full_farm_to_notification_api_flow(registration_db) -> None:
    client, session_factory = registration_db
    registered = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Farm owner", "phone": "09123456789", "password": "safe-password-123"},
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"phone": "09123456789", "password": "safe-password-123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    farm = client.post("/api/v1/farms", headers=headers, json={"name": "Main farm"})
    assert farm.status_code == 201
    plot = client.post(
        f"/api/v1/farms/{farm.json()['id']}/plots",
        headers=headers,
        json={"name": "North", "area_m2": 100},
    )
    assert plot.status_code == 201
    plot_id = plot.json()["id"]
    season = client.post(
        f"/api/v1/plots/{plot_id}/crop-seasons",
        headers=headers,
        json={"crop_name": "Wheat", "start_date": "2026-10-01"},
    )
    assert season.status_code == 201
    operation = client.post(
        f"/api/v1/plots/{plot_id}/operations",
        headers=headers,
        json={
            "title": "Irrigation",
            "operation_type": "irrigation",
            "crop_season_id": season.json()["id"],
            "scheduled_date": "2026-10-15",
            "scheduled_time": "12:00:00",
        },
    )
    assert operation.status_code == 201
    operation_id = operation.json()["id"]
    reminder = client.post(
        f"/api/v1/operations/{operation_id}/reminders",
        headers=headers,
        json={"remind_at": "2026-10-15T11:30:00+03:30"},
    )
    assert reminder.status_code == 201
    assert reminder.json()["remind_at"] == "2026-10-15T08:00:00.000000Z"
    with session_factory() as session:
        assert process_due_reminders(session, now="2026-10-15T08:00:00.000000Z") == 1
        assert process_due_reminders(session, now="2026-10-15T08:00:00.000000Z") == 0
    notifications = client.get("/api/v1/notifications", headers=headers)
    assert notifications.status_code == 200
    assert len(notifications.json()) == 1
    assert notifications.json()[0]["id"] == reminder.json()["id"]
    assert notifications.json()[0]["operation_title"] == "Irrigation"
    read = client.post(
        f"/api/v1/notifications/{reminder.json()['id']}/read", headers=headers
    )
    assert read.status_code == 200
    assert read.json()["read_at"] is not None
