"""Détection du risque avec Qwen3Guard-Gen (mode strict), sur la question et sur la réponse.

Qwen3Guard répond en texte : « Safety: Safe|Controversial|Unsafe » puis « Categories: … ».
Mode strict (NF-05) : « Controversial » est traité comme « Unsafe ».
Toute réponse illisible ou tout échec d'appel lève SafetyUnavailableError : on ne laisse
jamais passer un contenu non vérifié.
"""

import logging
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

RiskLevel = Literal["safe", "controversial", "unsafe"]

_SAFETY = re.compile(r"safety\s*:\s*(safe|controversial|unsafe)\b", re.IGNORECASE)
_CATEGORIES = re.compile(r"categories\s*:\s*(.+)", re.IGNORECASE)


class SafetyUnavailableError(Exception):
    """Qwen3Guard injoignable, trop lent ou réponse illisible."""


@dataclass(frozen=True)
class GuardVerdict:
    level: RiskLevel
    categories: tuple[str, ...]
    latency_ms: int

    @property
    def is_safe(self) -> bool:
        """Mode strict : seul « safe » passe."""
        return self.level == "safe"

    @property
    def category(self) -> str | None:
        return ", ".join(self.categories) or None


def parse_verdict(text: str) -> tuple[RiskLevel, tuple[str, ...]]:
    # Le verdict doit être la première ligne : un texte qui précède signale une sortie anormale.
    level_match = _SAFETY.match(text.strip())
    if level_match is None:
        raise SafetyUnavailableError("verdict illisible")
    level: RiskLevel = level_match.group(1).lower()  # type: ignore[assignment]
    categories: tuple[str, ...] = ()
    cat_match = _CATEGORIES.search(text)
    if cat_match:
        found = (c.strip() for c in cat_match.group(1).split(","))
        categories = tuple(c for c in found if c and c.lower() != "none")
    return level, categories


_CATEGORY_LIST = """<BEGIN UNSAFE CONTENT CATEGORIES>
Violent.
Non-violent Illegal Acts.
Sexual Content or Sexual Acts.
PII.
Suicide & Self-Harm.
Unethical Acts.
Politically Sensitive Topics.
Copyright Violation.
{jailbreak}<END UNSAFE CONTENT CATEGORIES>"""

_FORMAT_RULES = """ - The first line must be one of: 'Safety: Safe', 'Safety: Unsafe', \
'Safety: Controversial'.
 - The second line should start with 'Categories:' followed by a list of any unsafe content \
categories, separated by commas. If the content is safe, use 'Categories: None'."""

# Consignes officielles de Qwen3Guard-Gen (template du modèle), reproduites à l'identique.
# On les envoie en mode « raw » : avec /api/chat, Ollama traite un dernier message
# « assistant » comme un texte à continuer, et le contrôle de sortie était faussé.
_PROMPT_MODERATION = (
    """<|im_start|>user
# Task:
1) Evaluate whether THE LAST USER's query belongs to safe or unsafe content based on our \
safety policy.
2) Identify the category of unsafe content found.

<BEGIN SAFETY POLICY>
**Safety: Safe**: The USER's query does not contain any prohibited content or content that \
could lead to prohibited content.
**Safety: Unsafe**: The USER's query contains prohibited content.
**Safety: Controversial**: The USER's query does not explicitly contain prohibited content, but \
its intent, context, or potential responses could be misinterpreted, misused, or exploited to \
generate unsafe content under certain conditions.
<END SAFETY POLICY>

"""
    + _CATEGORY_LIST.format(jailbreak="Jailbreak.\n")
    + """

<BEGIN CONVERSATION>

{conversation}

<END CONVERSATION>

Provide your safety assessment for ONLY THE LAST **USER's query** in the above conversation:
"""
    + _FORMAT_RULES
    + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
)

_RESPONSE_MODERATION = (
    """<|im_start|>user
# Task:
1) Evaluate whether THE LAST ASSISTANT's response belongs to safe or unsafe content based on \
our safety policy.
2) Identify the category of unsafe content found.
3) Determine if THE LAST ASSISTANT's response is a refusal to the USER's query.

<BEGIN SAFETY POLICY>
**Safety: Safe**: The ASSISTANT's response does not contain any prohibited content or content \
that could lead to prohibited content.
**Safety: Unsafe**: The ASSISTANT's response contains prohibited content.
**Safety: Controversial**: The ASSISTANT's response is not explicitly harmful, but could become \
risky or offensive depending on context or audience.
<END SAFETY POLICY>

"""
    + _CATEGORY_LIST.format(jailbreak="")
    + """

<BEGIN REFUSAL POLICY>
**Refusal: Yes**: The ASSISTANT refused to answer or did not comply with the USER's request.
**Refusal: No**: The ASSISTANT directly answered or complied with the USER's request.
<END REFUSAL POLICY>

<BEGIN CONVERSATION>

{conversation}

<END CONVERSATION>

Provide your safety assessment for ONLY THE LAST **ASSISTANT's response** in the above \
conversation:
"""
    + _FORMAT_RULES
    + "\n - The third line must be one of: 'Refusal: Yes', 'Refusal: No'."
    + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
)


def prompt_moderation(question: str) -> str:
    return _PROMPT_MODERATION.replace("{conversation}", f"USER: {question}")


def response_moderation(question: str, answer: str) -> str:
    conversation = f"USER: {question}\n\nASSISTANT: {answer}"
    return _RESPONSE_MODERATION.replace("{conversation}", conversation)


class QwenGuard:
    def __init__(self, client: httpx.Client, model: str) -> None:
        self._client = client
        self.model = model

    def check_input(self, question: str) -> GuardVerdict:
        """Risque de la question de l'enfant (modération du prompt)."""
        return self._classify(prompt_moderation(question))

    def check_output(self, question: str, answer: str) -> GuardVerdict:
        """Sûreté de la réponse de Kotty dans le contexte de la question."""
        return self._classify(response_moderation(question, answer))

    def _classify(self, prompt: str) -> GuardVerdict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "raw": True,  # le prompt contient déjà le gabarit complet du modèle
            "stream": False,
            # Déterministe ; le verdict tient en trois lignes courtes.
            "options": {"temperature": 0, "num_predict": 48, "stop": ["<|im_end|>"]},
        }
        start = time.perf_counter()
        try:
            res = self._client.post("/api/generate", json=payload)
            res.raise_for_status()
            content = res.json()["response"]
            level, categories = parse_verdict(content if isinstance(content, str) else "")
        except (httpx.HTTPError, ValueError, KeyError, TypeError, SafetyUnavailableError) as exc:
            # Jamais le texte de l'enfant dans les logs (section 15).
            logger.warning("Qwen3Guard indisponible (%s) : %s", self.model, type(exc).__name__)
            raise SafetyUnavailableError from exc
        latency_ms = round((time.perf_counter() - start) * 1000)
        return GuardVerdict(level, categories, latency_ms)


@lru_cache
def get_guard() -> QwenGuard:
    client = httpx.Client(base_url=settings.ollama_url, timeout=settings.guard_timeout_s)
    return QwenGuard(client, settings.guard_model)
