from uuid import UUID

from sqlalchemy import select, text

from db import Farm


def authenticated_headers(client, *, phone: str) -> dict[str, str]:
    assert client.post(
        "/api/v1/auth/register",
        json={"full_name": "Farm owner", "phone": phone, "password": "safe-password-123"},
    ).status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"phone": phone, "password": "safe-password-123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_owner_can_manage_farm(registration_db) -> None:
    client, session_factory = registration_db
    assert client.get("/api/v1/farms").status_code == 401
    headers = authenticated_headers(client, phone="09123456789")

    created = client.post(
        "/api/v1/farms",
        headers=headers,
        json={"name": "  مزرعهٔ اول  ", "latitude": 35.7, "longitude": 51.4},
    )
    assert created.status_code == 201
    body = created.json()
    UUID(body["id"])
    assert body["name"] == "مزرعهٔ اول"
    assert body["timezone"] == "Asia/Tehran"
    assert body["created_at"] == body["updated_at"]
    assert client.get("/api/v1/farms", headers=headers).json()[0]["id"] == body["id"]
    assert client.get(f"/api/v1/farms/{body['id']}", headers=headers).status_code == 200

    changed = client.patch(
        f"/api/v1/farms/{body['id']}", headers=headers, json={"name": "مزرعهٔ دوم"}
    )
    assert changed.status_code == 200
    assert changed.json()["name"] == "مزرعهٔ دوم"
    with session_factory() as session:
        assert session.scalar(select(Farm).where(Farm.id == body["id"])).name == "مزرعهٔ دوم"

    assert client.delete(f"/api/v1/farms/{body['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/farms/{body['id']}", headers=headers).status_code == 404


def test_farm_access_is_limited_to_owner(registration_db) -> None:
    client, _ = registration_db
    owner_headers = authenticated_headers(client, phone="09123456789")
    other_headers = authenticated_headers(client, phone="09123456788")
    created = client.post("/api/v1/farms", headers=owner_headers, json={"name": "Private"})
    farm_id = created.json()["id"]

    assert client.get("/api/v1/farms", headers=other_headers).json() == []
    assert client.get(f"/api/v1/farms/{farm_id}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/v1/farms/{farm_id}", headers=other_headers, json={"name": "Stolen"}
    ).status_code == 404
    assert client.delete(f"/api/v1/farms/{farm_id}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/farms/{farm_id}", headers=owner_headers).json()["name"] == "Private"

    spoofed = client.post(
        "/api/v1/farms",
        headers=other_headers,
        json={"name": "Spoofed", "owner_id": created.json()["owner_id"]},
    )
    assert spoofed.status_code == 422


def test_coordinates_and_timezone_are_validated_on_create_and_update(registration_db) -> None:
    client, _ = registration_db
    headers = authenticated_headers(client, phone="09123456789")
    for payload in (
        {"name": "A", "latitude": 35.7},
        {"name": "A", "latitude": 91, "longitude": 51},
        {"name": "A", "timezone": "Invalid/Zone"},
        {"name": "   "},
    ):
        assert client.post("/api/v1/farms", headers=headers, json=payload).status_code == 422

    created = client.post("/api/v1/farms", headers=headers, json={"name": "Valid"})
    farm_id = created.json()["id"]
    assert client.patch(
        f"/api/v1/farms/{farm_id}", headers=headers, json={"latitude": 35.7}
    ).status_code == 422
    updated = client.patch(
        f"/api/v1/farms/{farm_id}",
        headers=headers,
        json={"latitude": 35.7, "longitude": 51.4, "timezone": "Asia/Tehran"},
    )
    assert updated.status_code == 200
    assert updated.json()["longitude"] == 51.4
    cleared = client.patch(
        f"/api/v1/farms/{farm_id}",
        headers=headers,
        json={"latitude": None, "longitude": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["latitude"] is None
    assert cleared.json()["longitude"] is None


def test_farm_with_dependent_record_cannot_be_deleted(registration_db) -> None:
    client, session_factory = registration_db
    headers = authenticated_headers(client, phone="09123456789")
    farm_id = client.post("/api/v1/farms", headers=headers, json={"name": "Keep"}).json()["id"]

    # Simulate a child table that later project steps will introduce.
    with session_factory() as session:
        session.execute(
            text(
                "CREATE TABLE farm_dependency ("
                "id TEXT PRIMARY KEY, farm_id TEXT NOT NULL "
                "REFERENCES farms(id) ON DELETE RESTRICT)"
            )
        )
        session.execute(
            text("INSERT INTO farm_dependency (id, farm_id) VALUES (:id, :farm_id)"),
            {"id": "dependent-1", "farm_id": farm_id},
        )
        session.commit()

    assert client.delete(f"/api/v1/farms/{farm_id}", headers=headers).status_code == 409
    assert client.get(f"/api/v1/farms/{farm_id}", headers=headers).status_code == 200
