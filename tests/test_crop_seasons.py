from sqlalchemy import select

from db import CropSeason


def auth_headers(client, phone: str) -> dict[str, str]:
    assert client.post(
        "/api/v1/auth/register",
        json={"full_name": "Crop owner", "phone": phone, "password": "safe-password-123"},
    ).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": phone, "password": "safe-password-123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_plot(client, headers: dict[str, str]) -> str:
    farm = client.post("/api/v1/farms", headers=headers, json={"name": "Test farm"})
    assert farm.status_code == 201
    plot = client.post(
        f"/api/v1/farms/{farm.json()['id']}/plots",
        headers=headers,
        json={"name": "North", "area_m2": 100},
    )
    assert plot.status_code == 201
    return plot.json()["id"]


def test_crop_season_create_read_update_delete(registration_db) -> None:
    client, session_factory = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    path = f"/api/v1/plots/{plot_id}/crop-seasons"
    created = client.post(
        path,
        headers=headers,
        json={
            "crop_name": "  گندم  ",
            "variety": "رقم الف",
            "start_date": "2026-10-15",
            "expected_end_date": "2027-04-20",
        },
    )
    assert created.status_code == 201
    body = created.json()
    season_id = body["id"]
    assert body["crop_name"] == "گندم"
    assert body["plot_id"] == plot_id
    assert body["status"] == "planned"
    assert body["created_at"] == body["updated_at"]
    assert client.get(path, headers=headers).json()[0]["id"] == season_id
    assert client.get(f"/api/v1/crop-seasons/{season_id}", headers=headers).status_code == 200

    updated = client.patch(
        f"/api/v1/crop-seasons/{season_id}",
        headers=headers,
        json={
            "actual_start_date": "2026-10-16",
            "actual_end_date": "2027-04-21",
            "status": "completed",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["actual_end_date"] == "2027-04-21"
    assert updated.json()["status"] == "completed"
    with session_factory() as session:
        assert session.scalar(select(CropSeason).where(CropSeason.id == season_id)).status == "completed"

    assert client.delete(f"/api/v1/plots/{plot_id}", headers=headers).status_code == 409
    assert client.delete(f"/api/v1/crop-seasons/{season_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/crop-seasons/{season_id}", headers=headers).status_code == 404


def test_invalid_dates_and_partial_updates_are_rejected(registration_db) -> None:
    client, _ = registration_db
    headers = auth_headers(client, "09123456789")
    plot_id = create_plot(client, headers)
    path = f"/api/v1/plots/{plot_id}/crop-seasons"
    for payload in (
        {"crop_name": "Wheat", "start_date": "2026-02-29"},
        {"crop_name": "Wheat", "start_date": "2026-2-01"},
        {"crop_name": "Wheat", "start_date": "2026-10-15T00:00:00"},
        {
            "crop_name": "Wheat",
            "start_date": "2026-10-15",
            "expected_end_date": "2026-10-14",
        },
        {
            "crop_name": "Wheat",
            "start_date": "2026-10-15",
            "actual_end_date": "2026-10-18",
        },
        {
            "crop_name": "Wheat",
            "start_date": "2026-10-15",
            "actual_start_date": "2026-10-18",
            "actual_end_date": "2026-10-17",
        },
    ):
        assert client.post(path, headers=headers, json=payload).status_code == 422

    created = client.post(
        path,
        headers=headers,
        json={
            "crop_name": "Wheat",
            "start_date": "2026-10-15",
            "expected_end_date": "2026-11-15",
        },
    )
    assert created.status_code == 201
    detail_path = f"/api/v1/crop-seasons/{created.json()['id']}"
    for change in (
        {"start_date": "2026-12-01"},
        {"actual_end_date": "2026-11-01"},
        {"start_date": None},
        {"status": "unknown"},
    ):
        assert client.patch(detail_path, headers=headers, json=change).status_code == 422


def test_crop_seasons_are_owner_scoped_and_may_overlap(registration_db) -> None:
    client, _ = registration_db
    owner = auth_headers(client, "09123456789")
    other = auth_headers(client, "09123456788")
    plot_id = create_plot(client, owner)
    path = f"/api/v1/plots/{plot_id}/crop-seasons"
    payload = {"crop_name": "Wheat", "start_date": "2026-10-15"}
    first = client.post(path, headers=owner, json=payload)
    second = client.post(path, headers=owner, json=payload)
    assert first.status_code == second.status_code == 201
    assert len(client.get(path, headers=owner).json()) == 2

    season_id = first.json()["id"]
    assert client.get(path, headers=other).status_code == 404
    assert client.post(path, headers=other, json=payload).status_code == 404
    assert client.get(f"/api/v1/crop-seasons/{season_id}", headers=other).status_code == 404
    assert client.patch(
        f"/api/v1/crop-seasons/{season_id}", headers=other, json={"status": "active"}
    ).status_code == 404
    assert client.delete(f"/api/v1/crop-seasons/{season_id}", headers=other).status_code == 404
    assert client.post(path, headers=owner, json={**payload, "plot_id": plot_id}).status_code == 422
