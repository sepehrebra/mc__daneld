import re

from sqlalchemy import select

from app.users.models import User
from app.users.router import password_hasher


def test_registration_hashes_password_and_normalizes_phone(registration_db) -> None:
    client, session_factory = registration_db
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "  Test User  ",
            "phone": "09123456789",
            "email": "Test@Example.com",
            "password": "safe-password-123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["phone"] == "+989123456789"
    assert body["full_name"] == "Test User"
    assert body["email"] == "test@example.com"
    assert "password" not in body and "password_hash" not in body
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", body["created_at"])
    assert body["created_at"] == body["updated_at"]

    with session_factory() as session:
        user = session.scalar(select(User).where(User.phone == "+989123456789"))
        assert user is not None
        assert user.password_hash != "safe-password-123"
        assert password_hasher.verify("safe-password-123", user.password_hash)


def test_duplicate_phone_and_email_are_rejected(registration_db) -> None:
    client, _ = registration_db
    first = {
        "full_name": "First User",
        "phone": "09123456789",
        "email": "first@example.com",
        "password": "safe-password-123",
    }
    assert client.post("/api/v1/auth/register", json=first).status_code == 201

    duplicate_phone = {**first, "phone": "+989123456789", "email": None}
    assert client.post("/api/v1/auth/register", json=duplicate_phone).status_code == 409

    duplicate_email = {**first, "phone": "09123456788", "email": "FIRST@example.com"}
    assert client.post("/api/v1/auth/register", json=duplicate_email).status_code == 409


def test_invalid_mobile_and_short_password_are_rejected(registration_db) -> None:
    client, _ = registration_db
    payload = {
        "full_name": "Test User",
        "phone": "02112345678",
        "password": "short",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 422
