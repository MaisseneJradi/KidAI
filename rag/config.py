"""Chemins, paramètres et localisation des outils externes (Poppler, Tesseract)."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "cnp"
MANIFEST = RAW_DIR / "manifest.json"
PROCESSED_DIR = ROOT / "data" / "processed" / "cnp"
PAGES_DIR = PROCESSED_DIR / "pages"  # un JSONL par PDF : texte page par page
CHUNKS_DIR = PROCESSED_DIR / "chunks"  # un JSONL par PDF : fragments + métadonnées
QDRANT_DIR = ROOT / "data" / "qdrant"  # Qdrant en mode local (pas de serveur, pas de Docker)

COLLECTION = "cnp_manuels"
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

# Découpage (cahier des charges, section 12) : ≈ 300–500 tokens, chevauchement 50.
CHUNK_TOKENS = 400
CHUNK_OVERLAP = 50
CHUNK_MIN_TOKENS = 30

OCR_DPI = 300
# Langue Tesseract selon la langue d'enseignement de la matière.
TESSERACT_LANG = {"ar": "ara", "fr": "fra", "en": "eng"}

# Langue d'enseignement par dossier de matière. On ne se fie pas au titre : les manuels
# d'anglais ont un titre en arabe.
SUBJECT_LANG = {
    "21_francais": "fr",
    "22_mathematique_fr": "fr",
    "23_physique": "fr",
    "24_chimie": "fr",
    "25_sciences_naturelles": "fr",
    "28_technologie": "fr",
    "29_economie_gestion": "fr",
    "33_informatique": "fr",
    "41_anglais": "en",
    "61_allemand": "de",
    "81_italien": "it",
    "91_espagnol": "es",
}


def subject_lang(subject: str) -> str:
    return SUBJECT_LANG.get(subject, "ar")


def grade_number(grade: str) -> int:
    """'4e_annee' -> 4, '0_preparatoire' -> 0."""
    return int(grade.split("_", 1)[0].rstrip("e"))


def _find(exe: str, candidates: list[tuple[Path, str]]) -> str:
    """Cherche dans le PATH, puis dans les emplacements d'installation connus (base, motif glob)."""
    found = shutil.which(exe)
    if found:
        return found
    for base, pattern in candidates:
        matches = sorted(base.glob(pattern), reverse=True) if base.is_dir() else []
        if matches:
            return str(matches[0])
    raise FileNotFoundError(f"{exe} introuvable : installez-le (voir rag/README.md)")


@lru_cache
def poppler(tool: str) -> str:
    """Chemin de pdftotext / pdftoppm / pdfinfo (POPPLER_BIN, PATH ou installation winget)."""
    if os.environ.get("POPPLER_BIN"):
        return str(Path(os.environ["POPPLER_BIN"]) / f"{tool}.exe")
    winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    return _find(tool, [(winget, f"oschwartz10612.Poppler_*/poppler-*/Library/bin/{tool}.exe")])


@lru_cache
def tesseract() -> str:
    if os.environ.get("TESSERACT_CMD"):
        return os.environ["TESSERACT_CMD"]
    return _find("tesseract", [(Path("C:/Program Files/Tesseract-OCR"), "tesseract.exe")])
