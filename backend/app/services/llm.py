"""Service LLM : génération des réponses de Kotty via Ollama (5 actions, Annexe C)."""

import logging
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import httpx

from app.core.age import AgeBand, age_band
from app.core.config import settings

logger = logging.getLogger(__name__)

Lang = Literal["fr", "ar"]
Action = Literal["ALLOW", "REWRITE", "REDIRECT", "ASK_ADULT", "BLOCK"]

# À incrémenter à chaque modification des textes ci-dessous (traçabilité MLflow / RL).
PROMPT_VERSION = "kotty-actions-v2"

_LANG_NAMES: dict[Lang, str] = {
    "fr": "français",
    "ar": "arabe standard moderne, avec un vocabulaire simple",
}

# Annexe C — préfixe commun (mascotte renommée Kotty).
_COMMON = (
    "Tu es Kotty, un assistant éducatif bienveillant pour un enfant de {age} ans en {grade}. "
    "Réponds en {lang}. Phrases courtes, mots simples adaptés à {age} ans, ton chaleureux et "
    "encourageant. Ne demande jamais d'informations personnelles. N'encourage jamais à garder "
    "un secret envers les parents."
)
# Fin du préfixe commun, sauf pour ASK_ADULT : on ne relance pas un enfant en détresse
# vers un autre sujet.
_CLOSING_QUESTION = "Termine par une petite question qui donne envie d'apprendre."

# Annexe C — consignes par action. Sans leçon (pas encore de RAG), {context} est omis.
_ACTION_WITH_CONTEXT: dict[Action, str] = {
    "ALLOW": (
        "Réponds à la question en t'appuyant si possible sur cette leçon : {context}. "
        "Donne un exemple de la vie de tous les jours."
    ),
    "REWRITE": (
        "La question touche un sujet délicat. Réponds avec douceur, sans détails choquants ni "
        "violents, en expliquant simplement et en rassurant. Leçon utile : {context}."
    ),
    "REDIRECT": (
        "Ne réponds pas à la demande telle quelle. Dis gentiment que tu ne peux pas aider sur ce "
        "point, puis propose une explication éducative et sûre sur un sujet proche, en "
        "t'appuyant sur : {context}."
    ),
}
_ACTION_NO_CONTEXT: dict[Action, str] = {
    "ALLOW": "Réponds à la question. Donne un exemple de la vie de tous les jours.",
    "REWRITE": (
        "La question touche un sujet délicat. Réponds avec douceur, sans détails choquants ni "
        "violents, en expliquant simplement et en rassurant."
    ),
    "REDIRECT": (
        "Ne réponds pas à la demande telle quelle. Dis gentiment que tu ne peux pas aider sur ce "
        "point, puis propose une explication éducative et sûre sur un sujet proche."
    ),
    "ASK_ADULT": (
        "Réponds en 2 à 3 phrases : valide l'émotion ou la curiosité de l'enfant, puis "
        "encourage-le à en parler à un parent ou à un adulte de confiance. "
        "Pas de conseil détaillé. "
        # Ajout étape 5 : le modèle approuvait un secret demandé par un adulte (signal d'emprise).
        "Ne dis jamais que garder un secret est bien : si quelqu'un lui demande de cacher quelque "
        "chose à ses parents, dis clairement que ce n'est pas un bon secret et qu'il a le droit "
        "d'en parler, qu'il ne sera pas grondé."
    ),
    "BLOCK": (
        "Réponds en 1 à 2 phrases : refuse poliment, sans culpabiliser, et propose de parler "
        "d'autre chose d'amusant ou d'intéressant."
    ),
}
# Actions dont la longueur suit l'âge ; ASK_ADULT et BLOCK ont leur propre longueur (courte).
_ANSWER_ACTIONS: tuple[Action, ...] = ("ALLOW", "REWRITE", "REDIRECT")
_SHORT_MAX_TOKENS = 200

# Consignes de longueur et de ton par tranche d'âge (objectif de l'étape 2).
_BAND_STYLE: dict[AgeBand, str] = {
    "small": (
        "Longueur : 2 à 3 phrases très courtes, 60 mots au maximum. N'utilise que des mots de "
        "tous les jours, aucun mot technique. Compare avec des choses familières (jouets, maison, "
        "animaux, cuisine). Ton très doux et joueur."
    ),
    "middle": (
        "Longueur : 4 à 5 phrases courtes, environ 100 mots au maximum. Tu peux introduire un ou "
        "deux mots nouveaux en les expliquant simplement. Ton enthousiaste et curieux."
    ),
    "teen": (
        "Longueur : 1 ou 2 petits paragraphes, environ 160 mots au maximum. Utilise le vrai "
        "vocabulaire scientifique en le définissant, explique les causes et les étapes avec "
        "précision. Ton complice et respectueux, jamais enfantin."
    ),
}

# Plafond de tokens générés : garde-fou seulement, la longueur est pilotée par le prompt.
_MAX_TOKENS: dict[AgeBand, int] = {"small": 250, "middle": 400, "teen": 700}
# Les tokens de réflexion comptent dans num_predict : budget ajouté quand think=true
# (mesuré : 1 800 à 3 400 tokens de réflexion avec qwen3:4b sur une question simple).
_THINK_BUDGET = 4096

_FORMAT = "Écris en texte simple, sans markdown, sans titres ni listes à puces."

# Réflexion restée dans le texte : bloc complet, ou fin de bloc sans balise ouvrante.
_THINK_BLOCK = re.compile(r"<think>.*?</think>|^.*</think>", re.DOTALL)


class LLMUnavailableError(Exception):
    """Ollama injoignable, trop lent, modèle absent ou réponse vide."""


@dataclass(frozen=True)
class LLMReply:
    text: str
    model_name: str
    prompt_version: str
    latency_ms: int


def format_grade(grade: str) -> str:
    """« 4e_annee » → « 4e année »."""
    return grade.replace("_annee", " année").replace("_", " ")


def build_system_prompt(
    age: int, grade: str, lang: Lang, context: str | None = None, action: Action = "ALLOW"
) -> str:
    common = _COMMON.format(age=age, grade=format_grade(grade), lang=_LANG_NAMES[lang])
    if action != "ASK_ADULT":
        common += " " + _CLOSING_QUESTION
    if context and action in _ACTION_WITH_CONTEXT:
        instruction = _ACTION_WITH_CONTEXT[action].format(context=context)
    else:
        instruction = _ACTION_NO_CONTEXT[action]
    parts = [common, instruction]
    if action in _ANSWER_ACTIONS:
        parts.append(_BAND_STYLE[age_band(age)])
    return "\n\n".join([*parts, _FORMAT])


def max_tokens(age: int, action: Action) -> int:
    return _MAX_TOKENS[age_band(age)] if action in _ANSWER_ACTIONS else _SHORT_MAX_TOKENS


class OllamaLLM:
    def __init__(self, client: httpx.Client, model: str, think: bool = False) -> None:
        self._client = client
        self.model = model
        self.think = think

    def answer(
        self, question: str, *, age: int, grade: str, lang: Lang, action: Action = "ALLOW"
    ) -> LLMReply:
        limit = max_tokens(age, action) + (_THINK_BUDGET if self.think else 0)
        system = build_system_prompt(age, grade, lang, action=action)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            "stream": False,
            # true : Ollama range la réflexion dans message.thinking, jamais montrée à l'enfant.
            "think": self.think,
            "options": {"temperature": 0.6, "num_predict": limit},
        }
        start = time.perf_counter()
        try:
            res = self._client.post("/api/chat", json=payload)
            res.raise_for_status()
            content = res.json()["message"]["content"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            # Jamais la question de l'enfant dans les logs (section 15).
            logger.warning("Ollama indisponible (%s) : %s", self.model, type(exc).__name__)
            raise LLMUnavailableError from exc
        latency_ms = round((time.perf_counter() - start) * 1000)

        # Vide aussi si la réflexion a épuisé num_predict avant la réponse.
        text = _THINK_BLOCK.sub("", content if isinstance(content, str) else "", count=1).strip()
        if not text:
            logger.warning("Ollama a renvoyé une réponse vide (%s)", self.model)
            raise LLMUnavailableError
        return LLMReply(text, self.model, PROMPT_VERSION, latency_ms)


@lru_cache
def get_llm() -> OllamaLLM:
    client = httpx.Client(base_url=settings.ollama_url, timeout=settings.ollama_timeout_s)
    return OllamaLLM(client, settings.ollama_model, think=settings.ollama_think)
