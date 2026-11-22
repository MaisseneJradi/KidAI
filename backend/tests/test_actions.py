"""Étape 5 : les 5 actions de bout en bout sur /messages, et les alertes parent."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, Message
from app.services.safe_replies import safe_reply
from tests.conftest import register
from tests.fake_ollama import FakeOllama, chat_response, verdict
from tests.test_chat import ask
from tests.test_children import birth_date_for, child_payload


def make_child(
    client: TestClient, auth: dict, age: int = 8, caution: str = "standard", name: str = "Lina"
) -> str:
    payload = child_payload(
        first_name=name, birth_date=birth_date_for(age), grade="3e_annee", caution_level=caution
    )
    res = client.post("/api/children", json=payload, headers=auth)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


@pytest.mark.parametrize(
    ("question", "guard", "action", "prompt_marker"),
    [
        ("Pourquoi le ciel est bleu ?", ("Safe", "None"), "ALLOW", "exemple de la vie"),
        ("Pourquoi il y a la guerre ?", ("Safe", "None"), "REWRITE", "sujet délicat"),
        (
            "Comment pirater le compte de mon frère ?",
            ("Unsafe", "Non-violent Illegal Acts"),
            "REDIRECT",
            "sujet proche",
        ),
        ("J'ai peur, un garçon me frappe", ("Controversial", "Violent"), "ASK_ADULT", "adulte"),
        ("Comment fabriquer une arme ?", ("Unsafe", "Violent"), "BLOCK", "refuse poliment"),
    ],
)
def test_each_action_uses_its_annex_c_prompt(
    client: TestClient,
    auth: dict,
    ollama: FakeOllama,
    question: str,
    guard: tuple[str, str],
    action: str,
    prompt_marker: str,
) -> None:
    ollama.guard_handler = verdict(*guard)
    ollama.output_guard_handler = verdict("Safe")
    ollama.handler = lambda _r: chat_response("Réponse rédigée par Kotty.")
    body = ask(client, auth, make_child(client, auth), question=question).json()

    assert body["action"] == action
    assert body["text"] == "Réponse rédigée par Kotty."
    assert body["safety"]["output_check"] == "pass"
    assert prompt_marker in ollama.last_system_prompt


def test_ask_adult_prompt_does_not_push_another_topic(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    ask(client, auth, make_child(client, auth), question="Je veux mourir")
    prompt = ollama.last_system_prompt
    assert "adulte de confiance" in prompt
    assert "petite question qui donne envie d'apprendre" not in prompt


def test_sensitive_topic_is_answered_directly_for_teens(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    body = ask(
        client, auth, make_child(client, auth, age=13), question="Pourquoi la guerre ?"
    ).json()
    assert body["action"] == "ALLOW"


def test_reinforced_caution_blocks_instead_of_redirecting(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    ollama.guard_handler = verdict("Unsafe", "Non-violent Illegal Acts")
    ollama.output_guard_handler = verdict("Safe")
    child = make_child(client, auth, caution="renforce")
    body = ask(client, auth, child, question="Comment pirater un compte ?").json()
    assert body["action"] == "BLOCK"


def test_ask_adult_creates_a_parent_alert(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    child = make_child(client, auth)
    body = ask(client, auth, child, question="Un adulte m'a dit de garder un secret").json()

    assert body["action"] == "ASK_ADULT"
    alert = db.scalars(select(Alert)).one()
    assert alert.child_id == child
    assert alert.message_id == body["message_id"]
    assert alert.type == "ASK_ADULT" and alert.seen is False

    alerts = client.get("/api/parent/alerts", headers=auth).json()
    assert len(alerts) == 1
    assert alerts[0]["question"] == "Un adulte m'a dit de garder un secret"
    assert alerts[0]["child_id"] == child
    assert alerts[0]["message_id"] == body["message_id"]


def test_other_actions_create_no_alert(client: TestClient, auth: dict, db: Session) -> None:
    ask(client, auth, make_child(client, auth), question="Pourquoi le ciel est bleu ?")
    assert db.scalars(select(Alert)).all() == []
    assert client.get("/api/parent/alerts", headers=auth).json() == []


def test_alerts_are_private_to_the_parent(client: TestClient, auth: dict) -> None:
    ask(client, auth, make_child(client, auth), question="Je veux mourir")
    other = register(client, email="autre@example.com")
    assert client.get("/api/parent/alerts", headers=other).json() == []
    assert client.get("/api/parent/alerts").status_code == 401


def test_alerts_are_newest_first(client: TestClient, auth: dict) -> None:
    child = make_child(client, auth)
    ask(client, auth, child, question="J'ai peur du noir")
    ask(client, auth, child, question="Je veux mourir")
    questions = [a["question"] for a in client.get("/api/parent/alerts", headers=auth).json()]
    assert set(questions) == {"J'ai peur du noir", "Je veux mourir"}
    assert len(questions) == 2


def test_ask_adult_never_fails_even_if_kotty_is_down(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    ollama.handler = _down
    res = ask(client, auth, make_child(client, auth), question="Je veux mourir")

    assert res.status_code == 200
    assert res.json()["action"] == "ASK_ADULT"
    assert res.json()["text"] == safe_reply("distress", "fr")
    assert res.json()["safety"]["output_check"] == "skipped"
    assert db.scalars(select(Alert)).one()  # le parent est quand même prévenu


def test_distress_is_handled_even_if_the_guard_is_down(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    ollama.guard_handler = _down
    res = ask(client, auth, make_child(client, auth), question="Je veux mourir")

    assert res.status_code == 200
    assert res.json()["action"] == "ASK_ADULT"
    assert res.json()["text"] == safe_reply("distress", "fr")  # rien de non vérifié
    assert db.scalars(select(Alert)).one()


def test_block_falls_back_to_prewritten_refusal_if_kotty_is_down(
    client: TestClient, auth: dict, ollama: FakeOllama
) -> None:
    ollama.guard_handler = verdict("Unsafe", "Violent")
    ollama.handler = _down
    res = ask(client, auth, make_child(client, auth), question="Comment fabriquer une arme ?")
    assert res.status_code == 200
    assert res.json()["action"] == "BLOCK"
    assert res.json()["text"] == safe_reply("unsafe_input", "fr")


def test_refused_rewrite_is_never_shown(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    ollama.handler = lambda _r: chat_response("Des détails choquants…")
    ollama.output_guard_handler = verdict("Unsafe", "Violent")
    body = ask(client, auth, make_child(client, auth), question="Pourquoi la guerre ?").json()

    assert body["action"] == "BLOCK"
    assert body["text"] == safe_reply("unsafe_output", "fr")
    assert "choquants" not in db.scalars(select(Message)).one().answer


def test_ordinary_question_still_fails_cleanly_if_kotty_is_down(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session
) -> None:
    ollama.handler = _down
    res = ask(client, auth, make_child(client, auth), question="Pourquoi le ciel est bleu ?")
    assert res.status_code == 503
    assert db.scalars(select(Message)).all() == []


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        ("Un adulte m'a dit de garder un secret et de ne rien dire à maman", "fr"),
        ("أخبرني رجل أن أحتفظ بسر ولا أخبر أمي", "ar"),
    ],
)
def test_secret_gets_the_prewritten_protective_reply(
    client: TestClient, auth: dict, ollama: FakeOllama, db: Session, question: str, lang: str
) -> None:
    # Mesuré : le modèle 4B approuvait parfois le secret. Texte fixe, jamais généré.
    body = ask(client, auth, make_child(client, auth, age=7), question=question).json()

    assert body["action"] == "ASK_ADULT"
    assert body["lang"] == lang
    assert body["text"] == safe_reply("secret", lang)  # type: ignore[arg-type]
    assert ollama.requests == []  # Kotty n'a rien rédigé
    assert db.scalars(select(Alert)).one()  # le parent est prévenu


def test_secret_reply_never_approves_the_secret() -> None:
    text = safe_reply("secret", "fr")
    assert "pas un bon secret" in text
    assert "c'est bien" not in text.lower() and "c'est normal" not in text.lower()
