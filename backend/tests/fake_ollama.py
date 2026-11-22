"""Faux serveur Ollama pour les tests (aucun appel réseau).

Il sert à la fois le LLM de Kotty et Qwen3Guard, distingués par le champ « model ».
"""

import json
from collections.abc import Callable

import httpx

from app.services.llm import OllamaLLM
from app.services.safety import QwenGuard

Handler = Callable[[httpx.Request], httpx.Response]

LLM_MODEL = "qwen3:4b"
GUARD_MODEL = "qwen3guard-test"


def chat_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})


def generate_response(text: str) -> httpx.Response:
    """Réponse de /api/generate (utilisé par Qwen3Guard en mode raw)."""
    return httpx.Response(200, json={"response": text, "done": True})


def verdict(level: str = "Safe", categories: str = "None") -> Handler:
    return lambda _req: generate_response(f"Safety: {level}\nCategories: {categories}")


class FakeOllama:
    def __init__(self) -> None:
        self.requests: list[dict] = []  # appels au LLM de Kotty
        self.guard_requests: list[dict] = []  # appels à Qwen3Guard
        self.handler: Handler = lambda _req: chat_response("Un volcan, c'est une montagne chaude.")
        self.guard_handler: Handler = verdict("Safe")
        # Verdict de sortie distinct, si besoin (sinon guard_handler).
        self.output_guard_handler: Handler | None = None

    def _dispatch(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["model"] == GUARD_MODEL:
            self.guard_requests.append(body)
            is_output = "THE LAST ASSISTANT's response" in body["prompt"]
            if is_output and self.output_guard_handler is not None:
                return self.output_guard_handler(request)
            return self.guard_handler(request)
        self.requests.append(body)
        return self.handler(request)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url="http://ollama.test", transport=httpx.MockTransport(self._dispatch)
        )

    def llm(self, think: bool = False) -> OllamaLLM:
        return OllamaLLM(self._client(), LLM_MODEL, think=think)

    def guard(self) -> QwenGuard:
        return QwenGuard(self._client(), GUARD_MODEL)

    @property
    def last_system_prompt(self) -> str:
        return self.requests[-1]["messages"][0]["content"]
