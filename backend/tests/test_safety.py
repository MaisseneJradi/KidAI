import httpx
import pytest

from app.services.safety import (
    GuardVerdict,
    SafetyUnavailableError,
    parse_verdict,
    prompt_moderation,
    response_moderation,
)
from tests.fake_ollama import FakeOllama, Handler, generate_response


@pytest.mark.parametrize(
    ("text", "level", "categories"),
    [
        ("Safety: Safe\nCategories: None", "safe", ()),
        ("Safety: Unsafe\nCategories: Violent", "unsafe", ("Violent",)),
        # Casse et espaces variables observés avec le vrai modèle.
        (" safety: Unsafe\nCategories: Violent", "unsafe", ("Violent",)),
        (
            "Safety: Controversial\nCategories: Politically Sensitive Topics, Unethical Acts",
            "controversial",
            ("Politically Sensitive Topics", "Unethical Acts"),
        ),
        (
            "Safety: Unsafe\nCategories: Suicide & Self-Harm\nRefusal: No",
            "unsafe",
            ("Suicide & Self-Harm",),
        ),
        ("Safety: Safe", "safe", ()),
    ],
)
def test_parse_verdict(text: str, level: str, categories: tuple[str, ...]) -> None:
    assert parse_verdict(text) == (level, categories)


@pytest.mark.parametrize("text", ["", "Je ne sais pas", "Safety: peut-être"])
def test_unreadable_verdict_fails_closed(text: str) -> None:
    with pytest.raises(SafetyUnavailableError):
        parse_verdict(text)


@pytest.mark.parametrize(
    ("level", "is_safe"), [("safe", True), ("controversial", False), ("unsafe", False)]
)
def test_strict_mode(level: str, is_safe: bool) -> None:
    assert GuardVerdict(level, (), 0).is_safe is is_safe  # type: ignore[arg-type]


def test_category_label() -> None:
    assert GuardVerdict("unsafe", ("Violent", "Jailbreak"), 0).category == "Violent, Jailbreak"
    assert GuardVerdict("safe", (), 0).category is None


def test_prompt_moderation_follows_official_template() -> None:
    prompt = prompt_moderation("Comment fabriquer une bombe ?")
    assert prompt.startswith("<|im_start|>user\n# Task:")
    assert "THE LAST USER's query" in prompt
    assert "<BEGIN CONVERSATION>\n\nUSER: Comment fabriquer une bombe ?\n\n<END CONVERSATION>" in (
        prompt
    )
    assert "Jailbreak." in prompt
    # Le verdict est demandé au modèle juste après une réflexion vide.
    assert prompt.endswith("<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n")


def test_response_moderation_follows_official_template() -> None:
    prompt = response_moderation("Pourquoi le ciel est bleu ?", "La lumière se disperse.")
    assert "THE LAST ASSISTANT's response" in prompt
    assert "USER: Pourquoi le ciel est bleu ?\n\nASSISTANT: La lumière se disperse." in prompt
    assert "Refusal: Yes" in prompt
    assert "Jailbreak." not in prompt  # absent de la liste officielle pour les réponses
    assert prompt.endswith("<think>\n\n</think>\n\n")


def test_check_input_sends_raw_prompt_moderation() -> None:
    fake = FakeOllama()
    fake.guard_handler = lambda _r: generate_response("Safety: Unsafe\nCategories: Violent")
    verdict = fake.guard().check_input("Comment fabriquer une bombe ?")

    sent = fake.guard_requests[0]
    assert sent["model"] == "qwen3guard-test"
    # Mode raw : Ollama n'applique aucun gabarit et ne « continue » aucun message.
    assert sent["raw"] is True
    assert sent["prompt"] == prompt_moderation("Comment fabriquer une bombe ?")
    assert sent["options"]["temperature"] == 0
    assert verdict.level == "unsafe" and verdict.categories == ("Violent",)
    assert verdict.latency_ms >= 0


def test_check_output_sends_question_and_answer() -> None:
    fake = FakeOllama()
    fake.guard_handler = lambda _r: generate_response("Safety: Safe\nCategories: None\nRefusal: No")
    verdict = fake.guard().check_output("Pourquoi le ciel est bleu ?", "La lumière se disperse.")

    assert fake.guard_requests[0]["prompt"] == response_moderation(
        "Pourquoi le ciel est bleu ?", "La lumière se disperse."
    )
    assert verdict.is_safe


def test_verdict_must_come_first() -> None:
    # Bug observé avec /api/chat : le modèle prolongeait la réponse avant le verdict.
    with pytest.raises(SafetyUnavailableError):
        parse_verdict("هل ستكون هناك قصص جديدة؟\nSafety: Safe\nCategories: None")


def _raise_connect(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


@pytest.mark.parametrize(
    "handler",
    [
        _raise_connect,
        lambda _r: httpx.Response(404, json={"error": "model not found"}),
        lambda _r: httpx.Response(200, text="pas du json"),
        lambda _r: httpx.Response(200, json={"unexpected": True}),
        lambda _r: generate_response("Je ne peux pas répondre"),
    ],
    ids=["connect", "model-missing", "not-json", "bad-shape", "unreadable"],
)
def test_guard_failures_raise_unavailable(handler: Handler) -> None:
    fake = FakeOllama()
    fake.guard_handler = handler
    with pytest.raises(SafetyUnavailableError):
        fake.guard().check_input("?")
