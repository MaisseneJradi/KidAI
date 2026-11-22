from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://kidai:kidai_dev@localhost:5432/kidai"
    cors_origins: list[str] = ["http://localhost:5173"]

    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    # Clé Fernet (chiffrement des données sensibles de l'enfant, NF-06).
    data_encryption_key: str = ""

    # LLM local (Ollama). Le frontend n'appelle jamais le modèle directement.
    ollama_url: str = "http://localhost:11434"
    # qwen3:4b-instruct : pas de réflexion, ~4 s par réponse (NF-01 < 5 s).
    # Avec qwen3:4b (variante « Thinking-2507 », 45-60 s), mettre ollama_think=True : Ollama
    # sépare alors la réflexion de la réponse.
    ollama_model: str = "qwen3:4b-instruct"
    ollama_think: bool = False
    ollama_timeout_s: float = 180.0

    # Classifieur de risque Qwen3Guard-Gen 0.6B (GGUF via Ollama), mode strict.
    guard_model: str = "hf.co/mradermacher/Qwen3Guard-Gen-0.6B-GGUF:Q8_0"
    guard_timeout_s: float = 30.0


settings = Settings()
