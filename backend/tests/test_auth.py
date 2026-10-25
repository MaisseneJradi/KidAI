from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Parent
from tests.conftest import register


def test_register_hashes_password_and_pin(client: TestClient, db: Session) -> None:
    register(client, email="Maman@Example.com")
    parent = db.scalar(select(Parent))
    assert parent is not None
    assert parent.email == "maman@example.com"
    assert parent.password_hash.startswith("$argon2")
    assert parent.pin_hash.startswith("$argon2")
    assert "motdepasse123" not in parent.password_hash


def test_register_twice_is_rejected(client: TestClient) -> None:
    register(client)
    res = client.post(
        "/api/auth/parent/register",
        json={"email": "parent@example.com", "password": "autremotdepasse", "pin": "0000"},
    )
    assert res.status_code == 409


def test_register_validates_input(client: TestClient) -> None:
    res = client.post(
        "/api/auth/parent/register",
        json={"email": "pas-un-email", "password": "court", "pin": "12a4"},
    )
    assert res.status_code == 422


def test_login(client: TestClient) -> None:
    register(client)
    ok = client.post(
        "/api/auth/parent/login",
        json={"email": "parent@example.com", "password": "motdepasse123"},
    )
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"

    bad = client.post(
        "/api/auth/parent/login",
        json={"email": "parent@example.com", "password": "mauvais-mot"},
    )
    assert bad.status_code == 401


def test_pin(client: TestClient, auth: dict) -> None:
    assert client.post("/api/auth/parent/pin", json={"pin": "1234"}, headers=auth).json() == {
        "ok": True
    }
    assert (
        client.post("/api/auth/parent/pin", json={"pin": "9999"}, headers=auth).status_code == 403
    )
    assert client.post("/api/auth/parent/pin", json={"pin": "1234"}).status_code == 401


def test_invalid_token_is_rejected(client: TestClient) -> None:
    res = client.get("/api/children", headers={"Authorization": "Bearer pas-un-jwt"})
    assert res.status_code == 401
