"""Chemins, vocabulaires et paramètres partagés par les étapes du pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "cache"
ANNOTATION = ROOT / "data" / "annotation"
PARAMS = ROOT / "params.yaml"

BASE_EN = PROCESSED / "base_en.parquet"
TRANSLATIONS = PROCESSED / "translations.parquet"
TRANSLATION_CACHE = CACHE / "translations.jsonl"
SYNTHETIC = PROCESSED / "synthetic.parquet"
SYNTHETIC_CACHE = CACHE / "synthetic.jsonl"
SYNTHETIC_TR_CACHE = CACHE / "synthetic_translations.jsonl"
DATASET = PROCESSED / "kidai_dataset.parquet"
PKU = PROCESSED / "pku_preferences.parquet"
THSAB = PROCESSED / "thsab_derja.parquet"
STATS_MD = PROCESSED / "kidai_stats.md"
STATS_JSON = PROCESSED / "kidai_stats.json"

OLLAMA_URL = "http://localhost:11434"

LANGS = ("fr", "ar", "derja", "en")
SOURCES = ("kidbench", "minorbench", "orbench", "safechild", "synthetic")
HARMS = ("safe", "borderline", "unsafe")
ACTIONS = ("ALLOW", "REWRITE", "REDIRECT", "ASK_ADULT", "BLOCK")
SPLITS = ("train", "val", "test")

# Sujets (≈ catégories de risque + matières scolaires) ; le RL peut aussi utiliser l'embedding.
TOPICS = (
    "curiosite",
    "sciences",
    "maths",
    "culture",
    "sante",
    "emotions",
    "relations",
    "ecole",
    "numerique",
    "morale",
    "sexualite",
    "violence",
    "discrimination",
    "danger",
    "substances",
    "illegal",
    "langage",
)

# Tranches d'âge du RL (section 11.2).
AGE_BANDS: tuple[tuple[int, int], ...] = ((6, 8), (9, 11), (12, 14))


def grade_of(age: int) -> str:
    """Âge -> année de l'enseignement de base tunisien (6 ans = 1re année, 14 ans = 9e)."""
    if not 6 <= age <= 14:
        raise ValueError(f"âge hors de 6-14 : {age}")
    n = age - 5
    return "1re_annee" if n == 1 else f"{n}e_annee"


def band_of(age: int) -> int:
    for i, (lo, hi) in enumerate(AGE_BANDS):
        if lo <= age <= hi:
            return i
    raise ValueError(f"âge hors de 6-14 : {age}")


def load_params() -> dict[str, Any]:
    with PARAMS.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
