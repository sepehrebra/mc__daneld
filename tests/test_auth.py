from sqlalchemy import select

from app.users.auth import token_digest
from db import AuthSession, User


def register_and_login(client) -> str:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "phone": "09123456789",
            "password": "safe-password-123",
        },
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"phone": "+989123456789", "password": "safe-password-123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    return login.json()["access_token"]


def test_login_current_user_and_logout(registration_db) -> None:
    client, session_factory = registration_db
    assert client.get("/api/v1/auth/me").status_code == 401
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["phone"] == "+989123456789"
    assert "password_hash" not in response.json()

    with session_factory() as session:
        stored = session.scalar(
            select(AuthSession).where(AuthSession.token_hash == token_digest(token))
        )
        assert stored is not None
        assert stored.token_hash != token
        assert stored.revoked_at is None

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_wrong_password_and_unknown_user_are_rejected(registration_db) -> None:
    client, _ = registration_db
    register_and_login(client)
    for phone in ("09123456789", "09123456788"):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": phone, "password": "wrong-password"},
        )
        assert response.status_code == 401


def test_expired_and_inactive_sessions_are_rejected(registration_db) -> None:
    client, session_factory = registration_db
    token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    with session_factory() as session:
        stored = session.scalar(select(AuthSession))
        stored.expires_at = "2000-01-01T00:00:00.000000Z"
        session.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"phone": "09123456789", "password": "safe-password-123"},
    )
    assert login.status_code == 200
    second_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    with session_factory() as session:
        user = session.scalar(select(User))
        user.is_active = 0
        session.commit()
    assert client.get("/api/v1/auth/me", headers=second_headers).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"phone": "09123456789", "password": "safe-password-123"},
    ).status_code == 401
