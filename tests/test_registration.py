import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.users.models import User
from app.users.router import password_hasher
from db import Base, get_db


@pytest.fixture
def registration_db() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    database_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(database_engine)
    session_factory = sessionmaker(bind=database_engine, expire_on_commit=False)

    def test_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        app.dependency_overrides.clear()
        database_engine.dispose()


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
