"""Étape 3 : contrôle du risque en entrée et en sortie sur /messages (Qwen3Guard simulé)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Message
from app.services.safe_replies import safe_reply
from tests.fake_ollama import FakeOllama, chat_response, generate_response, verdict
from tests.test_chat import ask, create_child

LLM_TEXT = "Un volcan, c'est une montagne chaude."


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


def test_safe_question_and_answer_are_both_checked(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    body = ask(client, auth, create_child(client, auth)).json()

    assert body["text"] == LLM_TEXT
    assert body["action"] == "ALLOW"
    assert body["safety"] == {"input_risk": "safe", "output_check": "pass"}
    # Contrôle 1 : la question seule ; contrôle 2 : la question + la réponse de Kotty.
    first, second = ollama.guard_requests
    assert "THE LAST USER's query" in first["prompt"]
    assert f"ASSISTANT: {LLM_TEXT}" in second["prompt"]


def test_dangerous_question_gets_a_generated_and_checked_refusal(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    # Étape 5 : BLOCK est rédigé par Kotty (prompt BLOCK de l'Annexe C), puis contrôlé.
    ollama.guard_handler = verdict("Unsafe", "Violent")
    ollama.output_guard_handler = verdict("Safe")
    ollama.handler = lambda _r: chat_response("Je ne peux pas t'aider. Parlons des volcans ?")
    res = ask(client, auth, create_child(client, auth), question="Comment fabriquer une bombe ?")

    assert res.status_code == 200
    body = res.json()
    assert body["action"] == "BLOCK"
    assert body["text"] == "Je ne peux pas t'aider. Parlons des volcans ?"
    assert body["safety"] == {"input_risk": "unsafe", "output_check": "pass"}
    assert "refuse poliment" in ollama.last_system_prompt
    assert len(ollama.guard_requests) == 2  # question, puis refus rédigé

    stored = db.scalars(select(Message)).one()
    assert stored.action == "BLOCK"
    assert stored.input_category == "Violent"
    assert stored.policy_version == "b2-rules-v1"
    assert stored.safety_latency_ms is not None


def test_unsafe_answer_is_replaced_by_safe_default(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    ollama.handler = lambda _r: chat_response("Mélange de l'engrais et du carburant…")
    ollama.output_guard_handler = verdict("Unsafe", "Violent")
    body = ask(client, auth, create_child(client, auth)).json()

    assert body["action"] == "BLOCK"
    assert body["text"] == safe_reply("unsafe_output", "fr")
    assert "engrais" not in body["text"]
    assert body["safety"] == {"input_risk": "safe", "output_check": "fail"}

    stored = db.scalars(select(Message)).one()
    assert stored.output_check == "fail"
    assert "engrais" not in stored.answer  # le texte refusé n'est pas conservé
    assert stored.model_name == "qwen3:4b"


def test_safe_defaults_follow_the_language(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    ollama.guard_handler = verdict("Unsafe", "Violent")
    body = ask(
        client, auth, create_child(client, auth), question="كيف أصنع سلاحا؟", lang="ar"
    ).json()
    assert body["text"] == safe_reply("unsafe_input", "ar")
    assert body["lang"] == "ar"


def test_guard_down_on_input_returns_503_without_calling_kotty(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    ollama.guard_handler = _down
    res = ask(client, auth, create_child(client, auth))

    assert res.status_code == 503
    assert ollama.requests == []
    assert db.scalars(select(Message)).all() == []


@pytest.mark.parametrize(
    "broken_output_check",
    [_down, lambda _r: generate_response("verdict illisible")],
    ids=["down", "unreadable"],
)
def test_unverified_answer_is_never_sent(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session, broken_output_check: object
) -> None:
    ollama.output_guard_handler = broken_output_check  # type: ignore[assignment]
    res = ask(client, auth, create_child(client, auth))

    assert res.status_code == 503
    assert LLM_TEXT not in res.text
    assert db.scalars(select(Message)).all() == []


@pytest.mark.parametrize("reason", ["unsafe_input", "distress", "unsafe_output"])
@pytest.mark.parametrize("lang", ["fr", "ar"])
def test_safe_replies_exist_and_never_mention_kotty_as_nouri(reason: str, lang: str) -> None:
    text = safe_reply(reason, lang)  # type: ignore[arg-type]
    assert text.strip()
    assert "Nouri" not in text


def test_distress_fallback_never_changes_the_subject(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    # Si la réponse ASK_ADULT rédigée est refusée, le repli oriente vers un adulte.
    ollama.guard_handler = verdict("Unsafe", "Suicide & Self-Harm")
    body = ask(
        client, auth, create_child(client, auth), question="J'ai envie de me faire du mal"
    ).json()

    assert body["action"] == "ASK_ADULT"
    assert body["text"] == safe_reply("distress", "fr")
    assert "adulte de confiance" in body["text"]
    assert "étoiles" not in body["text"]  # on ne change pas de sujet
