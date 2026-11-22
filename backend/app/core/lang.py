"""Langue de la réponse : celle des Réglages, sauf si la question est écrite en lettres arabes.

Un enfant qui écrit en arabe reçoit une réponse qu'il peut lire, même si l'appareil est en
français. La derja en lettres latines (« 3lech el sma zarga ») suit la langue des Réglages.
"""

from typing import Literal

Lang = Literal["fr", "ar"]


def _is_arabic_letter(char: str) -> bool:
    code = ord(char)
    return (
        0x0600 <= code <= 0x06FF  # arabe
        or 0x0750 <= code <= 0x077F  # supplément arabe
        or 0x08A0 <= code <= 0x08FF  # arabe étendu-A
        or 0xFB50 <= code <= 0xFDFF  # formes de présentation A
        or 0xFE70 <= code <= 0xFEFF  # formes de présentation B
    ) and char.isalpha()


def reply_lang(question: str, requested: Lang) -> Lang:
    """« ar » si la majorité des lettres de la question sont arabes, sinon la langue demandée."""
    letters = [c for c in question if c.isalpha()]
    if not letters:
        return requested
    arabic = sum(_is_arabic_letter(c) for c in letters)
    return "ar" if arabic * 2 > len(letters) else requested
