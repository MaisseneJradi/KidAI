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


settings = Settings()
