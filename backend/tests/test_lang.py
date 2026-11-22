import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.lang import reply_lang
from app.db.models import Message
from app.services.safe_replies import safe_reply
from tests.fake_ollama import FakeOllama, verdict
from tests.test_chat import ask, create_child


@pytest.mark.parametrize(
    ("question", "requested", "expected"),
    [
        ("كيف أصنع سلاحا؟", "fr", "ar"),
        ("لماذا السماء زرقاء؟", "ar", "ar"),
        ("Pourquoi le ciel est bleu ?", "fr", "fr"),
        # Langue de l'appareil conservée pour un texte en lettres latines.
        ("Pourquoi le ciel est bleu ?", "ar", "ar"),
        ("3lech el sma zarga ?", "fr", "fr"),
        # Un seul mot arabe dans une phrase française : on reste en français.
        ("Que veut dire سلام en français ?", "fr", "fr"),
        # Majorité arabe avec un mot latin : arabe.
        ("ما معنى كلمة bonjour بالعربية؟", "fr", "ar"),
        ("???", "fr", "fr"),
        ("123", "ar", "ar"),
    ],
)
def test_reply_lang(question: str, requested: str, expected: str) -> None:
    assert reply_lang(question, requested) == expected  # type: ignore[arg-type]


def test_arabic_question_on_french_device_gets_arabic_refusal(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    ollama.guard_handler = verdict("Unsafe", "Violent")
    body = ask(
        client, auth, create_child(client, auth), question="كيف أصنع سلاحا؟", lang="fr"
    ).json()

    assert body["lang"] == "ar"
    assert body["text"] == safe_reply("unsafe_input", "ar")
    assert db.scalars(select(Message)).one().lang == "ar"


def test_arabic_question_on_french_device_asks_kotty_in_arabic(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    body = ask(
        client, auth, create_child(client, auth), question="لماذا السماء زرقاء؟", lang="fr"
    ).json()

    assert body["lang"] == "ar"
    assert "Réponds en arabe" in ollama.last_system_prompt
