import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Message
from app.services.llm import PROMPT_VERSION
from tests.conftest import register
from tests.fake_ollama import FakeOllama
from tests.test_children import birth_date_for, child_payload


def create_child(client: TestClient, auth: dict, age: int = 9, grade: str = "4e_annee") -> str:
    payload = child_payload(birth_date=birth_date_for(age), grade=grade)
    res = client.post("/api/children", json=payload, headers=auth)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def ask(client: TestClient, auth: dict, child_id: str, **body: object) -> httpx.Response:
    return client.post(
        f"/api/chat/{child_id}/messages",
        json={"question": "Pourquoi les volcans explosent ?", "lang": "fr"} | body,
        headers=auth,
    )


def test_message_follows_api_contract(client: TestClient, auth: dict) -> None:
    child_id = create_child(client, auth)
    res = ask(client, auth, child_id)

    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body) == {
        "message_id",
        "text",
        "action",
        "lang",
        "rag_source",
        "image_status",
        "safety",
    }
    assert body["text"] == "Un volcan, c'est une montagne chaude."
    assert body["action"] == "ALLOW"
    assert body["lang"] == "fr"
    assert body["rag_source"] is None
    assert body["image_status"] == "none"
    assert body["safety"] == {"input_risk": "safe", "output_check": "pass"}


def test_message_is_stored_with_tracking_metadata(
    client: TestClient, auth: dict, db: Session
) -> None:
    child_id = create_child(client, auth)
    body = ask(client, auth, child_id, question="  C'est quoi une étoile ?  ", lang="ar").json()

    stored = db.scalars(select(Message)).one()
    assert stored.id == body["message_id"]
    assert stored.child_id == child_id
    assert stored.question == "C'est quoi une étoile ?"
    assert stored.answer == body["text"]
    assert stored.action == "ALLOW"
    assert stored.lang == "ar"
    assert stored.input_risk == "safe"
    assert stored.input_category is None
    assert stored.output_check == "pass"
    assert stored.rag_ref is None
    assert stored.model_name == "qwen3:4b"
    assert stored.prompt_version == PROMPT_VERSION
    assert stored.latency_ms >= stored.safety_latency_ms >= 0
    assert stored.created_at is not None


def test_prompt_depends_on_child_age_and_lang(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    young = create_child(client, auth, age=7, grade="2e_annee")
    teen = create_child(client, auth, age=13, grade="8e_annee")

    ask(client, auth, young)
    young_prompt = ollama.last_system_prompt
    ask(client, auth, teen, lang="ar")
    teen_prompt = ollama.last_system_prompt

    assert "enfant de 7 ans en 2e année" in young_prompt
    assert "60 mots au maximum" in young_prompt
    assert "enfant de 13 ans en 8e année" in teen_prompt
    assert "vocabulaire scientifique" in teen_prompt
    assert "Réponds en arabe" in teen_prompt


def test_other_parent_cannot_chat_with_child(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    child_id = create_child(client, auth)
    other = register(client, email="autre@example.com")

    assert ask(client, other, child_id).status_code == 404
    assert ask(client, auth, "inexistant").status_code == 404
    assert ollama.requests == ollama.guard_requests == []
    assert db.scalars(select(Message)).all() == []


def test_chat_requires_authentication(client: TestClient, auth: dict) -> None:
    child_id = create_child(client, auth)
    assert ask(client, {}, child_id).status_code == 401


def test_invalid_question_is_rejected(client: TestClient, auth: dict) -> None:
    child_id = create_child(client, auth)
    assert ask(client, auth, child_id, question="   ").status_code == 422
    assert ask(client, auth, child_id, question="x" * 501).status_code == 422
    assert ask(client, auth, child_id, lang="en").status_code == 422


def test_ollama_down_returns_clean_503(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    ollama.handler = down
    child_id = create_child(client, auth)
    res = ask(client, auth, child_id)

    assert res.status_code == 503
    assert res.json() == {"detail": "Kotty se repose un instant, réessaie dans un moment."}
    assert db.scalars(select(Message)).all() == []
