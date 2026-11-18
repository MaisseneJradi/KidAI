"""Client Ollama minimal (local) : une requête de chat dont la réponse est un JSON imposé."""

from __future__ import annotations

import json
import time
from typing import Any, Protocol

import requests

from prep import config


MAX_TOKENS = 800
TIMEOUT_S = 300


class OllamaUnavailable(Exception):
    """Ollama ne répond pas : on arrête tout plutôt que d'enregistrer de faux échecs."""


class ChatJson(Protocol):
    def __call__(self, prompt: str, schema: dict[str, Any], temperature: float) -> Any: ...


def string_list_schema(key: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {key: {"type": "array", "items": {"type": "string"}}},
        "required": [key],
    }


def ollama_chat_json(
    model: str,
    options: dict[str, Any] | None = None,
    url: str = config.OLLAMA_URL,
    retries: int = 3,
) -> ChatJson:
    """Renvoie une fonction prompt -> JSON décodé, via l'API /api/chat d'Ollama.

    `options` : options Ollama du modèle (ex. num_gpu). RuntimeError = échec de cette requête
    (réponse illisible ou erreur HTTP : certaines questions font échouer le modèle, sans que le
    service soit en cause) ; OllamaUnavailable = service injoignable.
    """

    def call(prompt: str, schema: dict[str, Any], temperature: float) -> Any:
        last: Exception | None = None
        for attempt in range(retries):
            try:
                r = requests.post(
                    f"{url}/api/chat",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "think": False,  # qwen3 : pas de raisonnement visible
                        "format": schema,
                        "options": {
                            "temperature": temperature,
                            # Sans limite, le modèle peut boucler (vu : 7 300 tokens, 34 min).
                            "num_predict": MAX_TOKENS,
                            **(options or {}),
                        },
                    },
                    timeout=TIMEOUT_S,
                )
            except requests.ConnectionError as e:
                last = e
                time.sleep(5 * (attempt + 1))
                continue
            except requests.Timeout as e:
                raise RuntimeError(f"{model} : pas de réponse en {TIMEOUT_S} s") from e
            if not r.ok:
                raise RuntimeError(f"{model} : erreur HTTP {r.status_code}")
            try:
                return json.loads(r.json()["message"]["content"])
            except (json.JSONDecodeError, KeyError) as e:
                raise RuntimeError(f"réponse illisible de {model} : {e}") from e
        raise OllamaUnavailable(f"Ollama ({model}) ne répond pas : {last}")

    return call
