import pytest
from fastapi.testclient import TestClient

from app.db import session
from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(("db_up", "expected"), [(True, "ok"), (False, "unavailable")])
def test_health(monkeypatch: pytest.MonkeyPatch, db_up: bool, expected: str) -> None:
    monkeypatch.setattr(session, "check_database", lambda: db_up)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": expected}
