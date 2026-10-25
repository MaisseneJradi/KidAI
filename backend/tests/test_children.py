from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.conftest import register


def birth_date_for(age: int) -> str:
    # Né un 1er janvier : l'anniversaire est toujours passé dans l'année.
    return date(date.today().year - age, 1, 1).isoformat()


def child_payload(**overrides: object) -> dict:
    payload = {
        "first_name": "Yasmine",
        "avatar": "🦊",
        "birth_date": birth_date_for(9),
        "sex": "fille",
        "grade": "4e_annee",
        "lang": "fr",
        "caution_level": "standard",
        "interests": ["espace", "animaux"],
        "needs": ["dyslexie"],
    }
    return payload | overrides


def test_create_and_list(client: TestClient, auth: dict) -> None:
    res = client.post("/api/children", json=child_payload(), headers=auth)
    assert res.status_code == 201, res.text
    child = res.json()
    assert child["age"] == 9
    assert child["sex"] == "fille"
    assert child["interests"] == ["espace", "animaux"]
    assert child["needs"] == ["dyslexie"]

    listed = client.get("/api/children", headers=auth).json()
    assert [c["id"] for c in listed] == [child["id"]]


def test_sensitive_fields_are_encrypted_in_database(
    client: TestClient, auth: dict, db: Session
) -> None:
    client.post("/api/children", json=child_payload(), headers=auth)
    birth, needs = db.execute(text("SELECT birth_date, needs FROM children")).one()
    assert "dyslexie" not in needs
    assert birth != child_payload()["birth_date"]


def test_children_are_private_to_their_parent(client: TestClient, auth: dict) -> None:
    child_id = client.post("/api/children", json=child_payload(), headers=auth).json()["id"]
    other = register(client, email="autre@example.com")

    assert client.get("/api/children", headers=other).json() == []
    assert client.patch(f"/api/children/{child_id}", json={}, headers=other).status_code == 404
    assert client.delete(f"/api/children/{child_id}", headers=other).status_code == 404


def test_update_and_delete(client: TestClient, auth: dict) -> None:
    child_id = client.post("/api/children", json=child_payload(), headers=auth).json()["id"]

    res = client.patch(
        f"/api/children/{child_id}",
        json={"birth_date": birth_date_for(12), "needs": [], "lang": "ar"},
        headers=auth,
    )
    assert res.status_code == 200
    assert res.json()["age"] == 12
    assert res.json()["needs"] == []
    assert res.json()["lang"] == "ar"
    assert res.json()["first_name"] == "Yasmine"

    assert client.delete(f"/api/children/{child_id}", headers=auth).status_code == 204
    assert client.get("/api/children", headers=auth).json() == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"birth_date": birth_date_for(4)},
        {"birth_date": birth_date_for(16)},
        {"sex": "autre"},
        {"needs": ["maladie_inventee"]},
        {"interests": ["cuisine"]},
        {"grade": "10e_annee"},
        {"first_name": "   "},
    ],
)
def test_invalid_child_is_rejected(client: TestClient, auth: dict, overrides: dict) -> None:
    res = client.post("/api/children", json=child_payload(**overrides), headers=auth)
    assert res.status_code == 422


def test_duplicates_are_removed(client: TestClient, auth: dict) -> None:
    res = client.post(
        "/api/children",
        json=child_payload(interests=["espace", "espace"], needs=["attention", "attention"]),
        headers=auth,
    )
    assert res.json()["interests"] == ["espace"]
    assert res.json()["needs"] == ["attention"]


def test_children_require_authentication(client: TestClient) -> None:
    assert client.get("/api/children").status_code == 401
    assert client.post("/api/children", json=child_payload()).status_code == 401
