import os

from cryptography.fernet import Fernet

# Secrets de test, définis avant l'import de l'application.
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["DATA_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.models import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db() -> Iterator[Session]:
    # SQLite en mémoire : rapide et isolé, les modèles n'utilisent que des types portables.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client: TestClient, email: str = "parent@example.com", pin: str = "1234") -> dict:
    res = client.post(
        "/api/auth/parent/register",
        json={"email": email, "password": "motdepasse123", "pin": pin},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def auth(client: TestClient) -> dict:
    return register(client)
