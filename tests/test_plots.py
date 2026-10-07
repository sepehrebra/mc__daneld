from sqlalchemy import select

from db import Plot


def auth_headers(client, phone: str) -> dict[str, str]:
    assert client.post(
        "/api/v1/auth/register",
        json={"full_name": "Plot owner", "phone": phone, "password": "safe-password-123"},
    ).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": phone, "password": "safe-password-123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_farm(client, headers: dict[str, str], name: str) -> str:
    response = client.post("/api/v1/farms", headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_plot_crud_and_parent_deletion_rule(registration_db) -> None:
    client, session_factory = registration_db
    headers = auth_headers(client, "09123456789")
    farm_id = create_farm(client, headers, "First farm")
    created = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        headers=headers,
        json={"name": "  North  ", "code": " N-1 ", "area_m2": 1250.5},
    )
    assert created.status_code == 201
    body = created.json()
    plot_id = body["id"]
    assert body["farm_id"] == farm_id
    assert body["name"] == "North"
    assert body["code"] == "N-1"
    assert body["area_m2"] == 1250.5
    assert body["created_at"] == body["updated_at"]
    assert client.get(f"/api/v1/farms/{farm_id}/plots", headers=headers).json()[0]["id"] == plot_id
    assert client.get(f"/api/v1/plots/{plot_id}", headers=headers).status_code == 200

    updated = client.patch(
        f"/api/v1/plots/{plot_id}",
        headers=headers,
        json={"area_m2": 1300, "code": None},
    )
    assert updated.status_code == 200
    assert updated.json()["area_m2"] == 1300
    assert updated.json()["code"] is None
    with session_factory() as session:
        assert session.scalar(select(Plot).where(Plot.id == plot_id)).area_m2 == 1300

    assert client.delete(f"/api/v1/farms/{farm_id}", headers=headers).status_code == 409
    assert client.delete(f"/api/v1/plots/{plot_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/plots/{plot_id}", headers=headers).status_code == 404
    assert client.delete(f"/api/v1/farms/{farm_id}", headers=headers).status_code == 204


def test_plot_ownership_cannot_be_bypassed(registration_db) -> None:
    client, _ = registration_db
    first = auth_headers(client, "09123456789")
    second = auth_headers(client, "09123456788")
    farm_id = create_farm(client, first, "Private farm")
    plot_id = client.post(
        f"/api/v1/farms/{farm_id}/plots",
        headers=first,
        json={"name": "Private plot", "area_m2": 100},
    ).json()["id"]

    assert client.get(f"/api/v1/farms/{farm_id}/plots").status_code == 401
    assert client.get(f"/api/v1/farms/{farm_id}/plots", headers=second).status_code == 404
    assert client.post(
        f"/api/v1/farms/{farm_id}/plots",
        headers=second,
        json={"name": "Intruder", "area_m2": 100},
    ).status_code == 404
    assert client.get(f"/api/v1/plots/{plot_id}", headers=second).status_code == 404
    assert client.patch(
        f"/api/v1/plots/{plot_id}", headers=second, json={"area_m2": 500}
    ).status_code == 404
    assert client.delete(f"/api/v1/plots/{plot_id}", headers=second).status_code == 404
    assert client.post(
        f"/api/v1/farms/{farm_id}/plots",
        headers=first,
        json={"name": "Spoofed", "area_m2": 100, "farm_id": farm_id},
    ).status_code == 422


def test_positive_area_and_per_farm_uniqueness(registration_db) -> None:
    client, _ = registration_db
    headers = auth_headers(client, "09123456789")
    farm_id = create_farm(client, headers, "First farm")
    second_farm_id = create_farm(client, headers, "Second farm")
    path = f"/api/v1/farms/{farm_id}/plots"

    for area in (0, -1):
        assert client.post(
            path, headers=headers, json={"name": "Invalid", "area_m2": area}
        ).status_code == 422
    for payload in (
        {"name": "   ", "area_m2": 1},
        {"name": "Valid", "code": "  ", "area_m2": 1},
    ):
        assert client.post(path, headers=headers, json=payload).status_code == 422

    first = client.post(
        path, headers=headers, json={"name": "North", "code": "N-1", "area_m2": 100}
    )
    assert first.status_code == 201
    assert client.post(
        path, headers=headers, json={"name": "North", "code": "Other", "area_m2": 100}
    ).status_code == 409
    assert client.post(
        path, headers=headers, json={"name": "South", "code": "N-1", "area_m2": 100}
    ).status_code == 409
    assert client.post(
        f"/api/v1/farms/{second_farm_id}/plots",
        headers=headers,
        json={"name": "North", "code": "N-1", "area_m2": 100},
    ).status_code == 201

    assert client.patch(
        f"/api/v1/plots/{first.json()['id']}", headers=headers, json={"area_m2": None}
    ).status_code == 422
