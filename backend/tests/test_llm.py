import httpx
import pytest

from app.core.age import age_band
from app.services.llm import (
    PROMPT_VERSION,
    LLMUnavailableError,
    build_system_prompt,
    format_grade,
)
from tests.fake_ollama import FakeOllama, Handler, chat_response


@pytest.mark.parametrize(
    ("age", "band"),
    [(6, "small"), (8, "small"), (9, "middle"), (11, "middle"), (12, "teen"), (14, "teen")],
)
def test_age_band(age: int, band: str) -> None:
    assert age_band(age) == band


def test_format_grade() -> None:
    assert format_grade("4e_annee") == "4e année"


def test_system_prompt_is_kotty_allow_from_annex_c() -> None:
    prompt = build_system_prompt(9, "4e_annee", "fr")
    assert "Tu es Kotty" in prompt
    assert "Nouri" not in prompt
    assert "enfant de 9 ans en 4e année" in prompt
    assert "Réponds en français" in prompt
    assert "Ne demande jamais d'informations personnelles" in prompt
    assert "N'encourage jamais à garder un secret" in prompt
    assert "exemple de la vie de tous les jours" in prompt
    # Pas de RAG à l'étape 2 : aucune leçon vide ou « None » dans le prompt.
    assert "leçon" not in prompt and "None" not in prompt


def test_system_prompt_uses_context_when_given() -> None:
    prompt = build_system_prompt(9, "4e_annee", "fr", context="Les volcans (p. 42)")
    assert "cette leçon : Les volcans (p. 42)" in prompt


def test_system_prompt_arabic() -> None:
    assert "Réponds en arabe" in build_system_prompt(10, "5e_annee", "ar")


def test_young_and_teen_prompts_differ() -> None:
    young = build_system_prompt(7, "2e_annee", "fr")
    teen = build_system_prompt(13, "8e_annee", "fr")
    assert "60 mots au maximum" in young and "aucun mot technique" in young
    assert "160 mots au maximum" in teen and "vocabulaire scientifique" in teen
    assert "jamais enfantin" not in young


def test_answer_calls_ollama_chat() -> None:
    fake = FakeOllama()
    reply = fake.llm().answer("Pourquoi le ciel est bleu ?", age=7, grade="2e_annee", lang="fr")

    sent = fake.requests[0]
    assert sent["model"] == "qwen3:4b"
    assert sent["stream"] is False
    assert sent["think"] is False
    assert sent["messages"][0]["role"] == "system"
    assert sent["messages"][1] == {"role": "user", "content": "Pourquoi le ciel est bleu ?"}
    assert reply.text == "Un volcan, c'est une montagne chaude."
    assert reply.model_name == "qwen3:4b"
    assert reply.prompt_version == PROMPT_VERSION
    assert reply.latency_ms >= 0


def test_token_cap_grows_with_age() -> None:
    fake = FakeOllama()
    llm = fake.llm()
    llm.answer("?", age=7, grade="2e_annee", lang="fr")
    llm.answer("?", age=13, grade="8e_annee", lang="fr")
    young, teen = (r["options"]["num_predict"] for r in fake.requests)
    assert young < teen


def test_thinking_model_gets_think_and_reasoning_budget() -> None:
    fake = FakeOllama()
    fake.llm(think=False).answer("?", age=7, grade="2e_annee", lang="fr")
    fake.llm(think=True).answer("?", age=7, grade="2e_annee", lang="fr")
    plain, thinking = fake.requests
    assert plain["think"] is False and thinking["think"] is True
    assert thinking["options"]["num_predict"] > plain["options"]["num_predict"] + 1000


def test_thinking_field_is_never_returned() -> None:
    fake = FakeOllama()
    fake.handler = lambda _r: httpx.Response(
        200,
        json={"message": {"content": "Le ciel est bleu.", "thinking": "Okay, the user asks…"}},
    )
    reply = fake.llm(think=True).answer("?", age=9, grade="4e_annee", lang="fr")
    assert reply.text == "Le ciel est bleu."


@pytest.mark.parametrize(
    "content",
    [
        "<think>hmm</think>\n\nLe ciel est bleu.",
        # Variante Thinking appelée avec think=false : la balise ouvrante est dans le template.
        "Okay, the user is 7 years old…\n</think>\n\nLe ciel est bleu.",
    ],
)
def test_leaked_reasoning_is_removed(content: str) -> None:
    fake = FakeOllama()
    fake.handler = lambda _r: chat_response(content)
    assert fake.llm().answer("?", age=9, grade="4e_annee", lang="fr").text == "Le ciel est bleu."


def _raise_connect(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


def _raise_timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("slow", request=request)


@pytest.mark.parametrize(
    "handler",
    [
        _raise_connect,
        _raise_timeout,
        lambda _r: httpx.Response(404, json={"error": "model 'qwen3:4b' not found"}),
        lambda _r: httpx.Response(500, text="boom"),
        lambda _r: httpx.Response(200, text="pas du json"),
        lambda _r: httpx.Response(200, json={"unexpected": True}),
        lambda _r: chat_response("   "),
        lambda _r: chat_response("<think>seulement du raisonnement</think>"),
    ],
    ids=["connect", "timeout", "model-missing", "500", "not-json", "bad-shape", "blank", "think"],
)
def test_ollama_failures_raise_unavailable(handler: Handler) -> None:
    fake = FakeOllama()
    fake.handler = handler
    with pytest.raises(LLMUnavailableError):
        fake.llm().answer("?", age=9, grade="4e_annee", lang="fr")
