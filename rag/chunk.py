"""Découpage du texte des manuels en fragments indexables (cahier des charges, section 12).

Deux niveaux de titres sont reconnus :
  - l'unité  : « الوحدة », « المحور », « المجال », « Module », « Unit »... ;
  - la leçon : « الموضوع », « الدرس », « الحصة », « Leçon », « Séance », « Lesson »...
Un fragment ne mélange jamais deux leçons (ni deux unités) ; chaque section est ensuite
découpée en fenêtres de ≈ CHUNK_TOKENS tokens avec un chevauchement de CHUNK_OVERLAP tokens.
Les en-têtes de page répétés (« الوحدة 2 : جسم الإنسان 35 ») ne créent pas de nouvelle section.
Chaque fragment garde ses métadonnées : grade, subject, lang, book_title, unit, chapter, page.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass

from rag import config
from rag.extract import Document
from rag.text_quality import clean

_SEP = r"(?:\s*[:：\-–]|\s+\d|\s*$)"
UNIT_HEADING = re.compile(
    rf"^\s*(?:(?:الوحدة|المحور|المجال|الكفاية){_SEP}|(?:Module|Unit|Domaine)\b)", re.IGNORECASE
)
LESSON_HEADING = re.compile(
    rf"^\s*(?:(?:الموضوع|الدرس|الحصة){_SEP}"
    r"|(?:Le[çc]on|S[ée]quence|S[ée]ance|Chapitre|Lesson|Chapter)\b)",
    re.IGNORECASE,
)
MAX_HEADING_CHARS = 90

TokenCounter = Callable[[str], int]


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    book_title: str
    unit: str
    chapter: str  # leçon (ou unité si aucune leçon n'est détectée)
    grade: str
    grade_num: int
    subject: str
    category: str
    lang: str
    page: int  # première page du fragment
    page_end: int
    url: str

    def payload(self) -> dict:
        return asdict(self)


def heading_of(line: str) -> tuple[str, str] | None:
    """('unit' | 'lesson', intitulé) si la ligne est un titre, sinon None.

    L'intitulé est débarrassé du numéro de page final et de la ponctuation.
    """
    if len(line) > MAX_HEADING_CHARS:
        return None
    kind = "lesson" if LESSON_HEADING.match(line) else "unit" if UNIT_HEADING.match(line) else None
    if kind is None:
        return None
    title = re.sub(r"[\s\d\"'«».:：\-–]+$", "", line).strip(" :：-–\"'«»")
    return kind, re.sub(r"\s*[:：]\s*", " : ", title)


def _sections(pages: list[dict]) -> list[tuple[str, str, list[tuple[str, int]]]]:
    """Regroupe les lignes nettoyées par section (unité, leçon) — voir la doc du module."""
    unit = lesson = ""
    sections: list[tuple[str, str, list[tuple[str, int]]]] = [("", "", [])]
    pending: tuple[str, str] | None = None  # titre réduit au mot-clé : intitulé à la ligne suivante

    def start(kind: str, title: str) -> bool:
        nonlocal unit, lesson
        if (kind == "unit" and title == unit) or (kind == "lesson" and title == lesson):
            return False  # en-tête de page répété
        if kind == "unit":
            unit, lesson = title, ""
        else:
            lesson = title
        sections.append((unit, lesson, []))
        return True

    for page in pages:
        for line in clean(page["text"]).splitlines():
            if pending:
                kind, keyword = pending
                pending = None
                if start(kind, f"{keyword} : {line}"):
                    sections[-1][2].append((keyword, page["page"]))
            elif heading := heading_of(line):
                kind, title = heading
                if len(title.split()) <= 1:
                    pending = heading
                    continue
                if not start(kind, title):
                    continue  # on n'indexe pas les en-têtes répétés
            sections[-1][2].append((line, page["page"]))
    return sections


def _windows(
    lines: list[tuple[str, int]], count: TokenCounter
) -> Iterable[tuple[list[tuple[str, int]], int]]:
    """Regroupe des lignes (texte, page) en fenêtres de ≈ CHUNK_TOKENS avec chevauchement."""
    window: list[tuple[str, int, int]] = []  # (texte, page, tokens)
    size = 0
    for text, page in lines:
        n = count(text)
        if n > config.CHUNK_TOKENS:  # ligne très longue : on la coupe en morceaux de mots
            if window:
                yield [(t, p) for t, p, _ in window], size
                window, size = [], 0
            words = text.split()
            step = max(1, len(words) * config.CHUNK_TOKENS // n)
            parts = [" ".join(words[i : i + step]) for i in range(0, len(words), step)]
            yield from _windows([(p, page) for p in parts], count)
            continue
        if size + n > config.CHUNK_TOKENS and window:
            yield [(t, p) for t, p, _ in window], size
            # chevauchement : on reprend les dernières lignes (≈ CHUNK_OVERLAP tokens)
            kept: list[tuple[str, int, int]] = []
            kept_size = 0
            for item in reversed(window):
                if kept_size >= config.CHUNK_OVERLAP:
                    break
                kept.insert(0, item)
                kept_size += item[2]
            window, size = kept, kept_size
        window.append((text, page, n))
        size += n
    if window:
        yield [(t, p) for t, p, _ in window], size


def chunk_document(doc: Document, pages: list[dict], count: TokenCounter) -> list[Chunk]:
    chunks: list[Chunk] = []
    for unit, lesson, lines in _sections(pages):
        for window, size in _windows(lines, count):
            if size < config.CHUNK_MIN_TOKENS:
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}-{len(chunks):04d}",
                    doc_id=doc.doc_id,
                    text="\n".join(t for t, _ in window),
                    book_title=doc.title,
                    unit=unit,
                    chapter=lesson or unit,
                    grade=doc.grade,
                    grade_num=config.grade_number(doc.grade),
                    subject=doc.subject,
                    category=doc.category,
                    lang=doc.lang,
                    page=window[0][1],
                    page_end=window[-1][1],
                    url=doc.url,
                )
            )
    return chunks


def bge_token_counter() -> TokenCounter:
    """Compte les tokens avec le tokenizer de bge-m3 (le même que pour les embeddings)."""
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(config.EMBEDDING_MODEL)
    return lambda text: len(tokenizer.encode(text, add_special_tokens=False))
