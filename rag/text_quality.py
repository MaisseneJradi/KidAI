"""Qualité du texte extrait d'un PDF et nettoyage.

Les manuels CNP mélangent trois cas (voir le diagnostic du 25/10/2026) :
  - texte Unicode propre (français, anglais) -> pdftotext suffit ;
  - arabe en police non Unicode -> « ¢üædG áHÉàµd » : illisible, il faut l'OCR ;
  - arabe en formes de présentation, dans l'ordre visuel -> trop abîmé, OCR aussi.
"""

from __future__ import annotations

import re
import unicodedata

AR_BASE = re.compile(r"[ء-ي]")
AR_PRESENTATION = re.compile(r"[ﭐ-﷿ﹰ-ﻼ]")
LATIN = re.compile(r"[A-Za-z]")
FRENCH_ACCENTS = set("éèêëàâäçùûüôöîïÉÈÊÀÂÇÙÛÔÎœŒ")
# Symboles typiques d'une police arabe non Unicode lue en Latin-1 / MacRoman.
SUSPECT = re.compile(
    r"[¡-¿×÷‘-„†-•…‰"
    r"∀-⋿ˆ-˝Ωπƒ™◊]"
)
TASHKEEL = re.compile(r"[ً-ْٰـ]")  # voyelles brèves, shadda, tatweel
BIDI_MARKS = re.compile(r"[‎‏‪-‮⁦-⁩]")

MIN_LETTERS = 30


def suspect_count(text: str) -> int:
    return len(SUSPECT.findall(text)) + sum(
        1 for c in text if "À" <= c <= "ÿ" and c not in FRENCH_ACCENTS
    )


def is_usable(text: str, lang: str) -> bool:
    """Le texte extrait par pdftotext est-il exploitable tel quel pour cette langue ?"""
    base = len(AR_BASE.findall(text))
    pres = len(AR_PRESENTATION.findall(text))
    latin = len(LATIN.findall(text))
    suspect = suspect_count(text)
    letters = base + pres + latin + suspect
    if letters < MIN_LETTERS:
        return False  # page vide, scannée ou texte vectorisé
    if suspect / letters > 0.08:
        return False  # police non Unicode
    if lang == "ar":
        return base >= MIN_LETTERS and pres <= 0.3 * base
    return latin >= MIN_LETTERS


def clean(text: str) -> str:
    """Normalise le texte pour l'index : formes de présentation, diacritiques, bruit d'OCR."""
    text = unicodedata.normalize("NFKC", text)
    text = BIDI_MARKS.sub("", text)
    text = TASHKEEL.sub("", text)  # les questions des enfants n'ont pas de voyelles
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        # numéros de page, puces isolées, bruit d'OCR (©, |, ...)
        if not line or re.fullmatch(r"[\d\W_]{0,4}", line):
            continue
        lines.append(line)
    return "\n".join(lines)
