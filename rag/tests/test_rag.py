from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from rag import config
from rag.chunk import _sections, chunk_document, heading_of
from rag.extract import Document
from rag.index import ensure_collection, index_chunks, point_id
from rag.search import search
from rag.text_quality import clean, is_usable

# --------------------------------------------------------------------------- qualité du texte

# Extraits réels de pdftotext sur les manuels CNP.
LEGACY_FONT = "q…Oô°q ùdG ¢q üqædG áHÉàµd §q£NCG …Oô q °ùdG q ¢üædG q á«æH : ∫hCq ’G ¢SQódG"
PRESENTATION_FORMS = "ﻴﻄﺎ‬‫ﻋﺪ َﺧ ِﻠ ً‬ ‫ﺨ َﺒ َﺰ ِﺓ‪َ .‬ﺭ ﱠﺣ َﺐ ِﺑ َﻨﺎ ٱﻟْ َ ﺨ ﱠﺒ ُﺎﺯ َﻭ ﺃَ َ ﱠ ﻠﻤ َﺘ َﻨﺎ ِﺇﻟَﻰ ٱﻟْ َﻤ ْ ﺖ ﺸﺮ"
CLEAN_ARABIC = "التحقت خلود بأخيها مروان وهو يطالع الموسوعة العلمية فطرحت عليه التساؤل التالي"
CLEAN_FRENCH = "Module d'apprentissage 3 — J'apprends à mieux connaître le monde des animaux"


def test_is_usable_detects_broken_arabic() -> None:
    assert not is_usable(LEGACY_FONT, "ar")
    assert not is_usable(PRESENTATION_FORMS, "ar")
    assert is_usable(CLEAN_ARABIC, "ar")


def test_is_usable_french_and_empty_pages() -> None:
    assert is_usable(CLEAN_FRENCH, "fr")
    assert not is_usable("  12  ", "fr")
    assert not is_usable(LEGACY_FONT, "fr")


def test_clean_normalizes_arabic_and_drops_noise() -> None:
    text = "أُسَمِّي الأَعْضاءَ\n30\n©\n‫ﺍﻟﺨﺒﺰ‬"
    assert clean(text) == "أسمي الأعضاء\nالخبز"


# --------------------------------------------------------------------------- découpage

DOC = Document(
    doc_id="103404P00",
    path=Path("x.pdf"),
    title="الإيقاظ العلمي",
    grade="4e_annee",
    subject="03_eveil_scientifique",
    category="eleve",
    lang="ar",
    url="https://cnp.com.tn/arabic/PDF/103404P00.pdf",
)


def words(text: str) -> int:
    return len(text.split())


def test_heading_detection() -> None:
    assert heading_of("الموضوع: تكيف العضو مع نمط التنقل.") == (
        "lesson",
        "الموضوع : تكيف العضو مع نمط التنقل",
    )
    # en-tête de page : le numéro de page final est retiré
    assert heading_of("الوحدة 2 : جسم الإنسان 35") == ("unit", "الوحدة 2 : جسم الإنسان")
    assert heading_of("Module d'apprentissage") == ("unit", "Module d'apprentissage")
    assert heading_of("Leçon 4 : les volcans") == ("lesson", "Leçon 4 : les volcans")
    assert heading_of("أرسم الطرف الأمامي والخلفي لأرنب") is None
    assert heading_of("الموضوعات المقترحة للنقاش") is None  # le mot-clé doit être isolé
    assert heading_of("الموضوع " + "طويل " * 40) is None  # trop long pour un titre


def test_repeated_page_headers_and_split_titles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CHUNK_MIN_TOKENS", 1)
    pages = [
        {"page": 1, "text": "المحور\nالحواس ودورها\nالموضوع : حاسة البصر\nالعين عضو الإبصار عند الإنسان"},
        {"page": 2, "text": "المحور : الحواس ودورها 2\nللعين أجزاء كثيرة تحميها من الأذى"},
    ]
    sections = [(u, lesson) for u, lesson, lines in _sections(pages) if lines]
    assert sections == [
        ("المحور : الحواس ودورها", ""),
        ("المحور : الحواس ودورها", "الموضوع : حاسة البصر"),
    ]
    chunks = chunk_document(DOC, pages, words)
    assert all("المحور : الحواس ودورها 2" not in c.text for c in chunks)  # en-tête répété ignoré
    assert chunks[-1].chapter == "الموضوع : حاسة البصر"
    assert chunks[-1].unit == "المحور : الحواس ودورها"


def test_chunks_follow_lessons_and_keep_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CHUNK_TOKENS", 40)
    monkeypatch.setattr(config, "CHUNK_OVERLAP", 10)
    monkeypatch.setattr(config, "CHUNK_MIN_TOKENS", 3)
    def line(i: int) -> str:
        return f"النسر طائر يطير عاليا في السماء بفضل جناحيه رقم{i}"  # 9 mots, tous différents

    pages = [
        {
            "page": 30,
            "text": "الموضوع : تكيف العضو مع نمط التنقل\n" + "\n".join(line(i) for i in range(8)),
        },
        {
            "page": 31,
            "text": "\n".join(line(i) for i in range(8, 10))
            + "\nالموضوع : التنفس عند الإنسان\n"
            + line(10),
        },
    ]
    chunks = chunk_document(DOC, pages, words)

    first = [c for c in chunks if "التنقل" in c.chapter]
    second = [c for c in chunks if "التنفس" in c.chapter]
    assert len(first) >= 2 and len(second) == 1  # la leçon longue est découpée
    assert all(words(c.text) <= 40 for c in chunks)
    assert first[0].page == 30 and first[-1].page_end == 31
    assert second[0].page == 31 and "رقم10" in second[0].text and "رقم9" not in second[0].text
    # chevauchement : le début d'un fragment reprend les dernières lignes du précédent
    head = first[1].text.splitlines()[0]
    assert head in first[0].text.splitlines()[-2:]
    # aucune ligne perdue
    assert all(any(f"رقم{i}" in c.text for c in first) for i in range(10))
    c = first[0]
    assert (c.grade, c.grade_num, c.subject, c.lang, c.book_title) == (
        "4e_annee", 4, "03_eveil_scientifique", "ar", "الإيقاظ العلمي"
    )
    assert len({c.chunk_id for c in chunks}) == len(chunks)


# --------------------------------------------------------------------------- index + recherche


def fake_embed(texts):
    """Embedding déterministe : un axe par mot-clé (suffisant pour tester le filtrage)."""
    keys = ["نسر", "تنفس", "volcan", "plante"]
    vectors = []
    for t in texts:
        v = [1.0 if k in t else 0.0 for k in keys] + [0.0] * (config.EMBEDDING_DIM - len(keys))
        v[-1] = 0.01  # jamais de vecteur nul
        vectors.append(v)
    return vectors


@pytest.fixture
def qc() -> QdrantClient:
    qc = QdrantClient(":memory:")
    ensure_collection(qc)
    return qc


def make_chunk(chunk_id: str, text: str, grade_num: int, lang: str):
    from rag.chunk import Chunk

    return Chunk(
        chunk_id=chunk_id, doc_id="d", text=text, book_title="Livre", unit="Unité", chapter="Leçon",
        grade=f"{grade_num}e_annee", grade_num=grade_num, subject="03_eveil_scientifique",
        category="eleve", lang=lang, page=1, page_end=1, url="u",
    )


def test_index_is_idempotent(qc: QdrantClient) -> None:
    chunks = [make_chunk("a", "النسر يطير", 4, "ar"), make_chunk("b", "التنفس", 6, "ar")]
    assert index_chunks(chunks, fake_embed, qc, progress=lambda _m: None) == 2
    assert index_chunks(chunks, fake_embed, qc, progress=lambda _m: None) == 0
    assert qc.count(config.COLLECTION).count == 2
    assert point_id("a") == point_id("a") != point_id("b")


def test_search_filters_by_grade_and_language(qc: QdrantClient) -> None:
    chunks = [
        make_chunk("nisr4", "النسر يطير عاليا", 4, "ar"),
        make_chunk("nisr8", "النسر طائر جارح", 8, "ar"),
        make_chunk("volcan", "Le volcan crache de la lave", 5, "fr"),
    ]
    index_chunks(chunks, fake_embed, qc, progress=lambda _m: None)

    hits = search("لماذا يطير النسر", max_grade=5, lang="ar", embed=fake_embed, qc=qc)
    assert [h.chunk_id for h in hits] == ["nisr4"]  # le manuel de 8e est filtré

    assert search("النسر", max_grade=9, lang="fr", embed=fake_embed, qc=qc) == []
    assert {h.chunk_id for h in search("النسر", embed=fake_embed, qc=qc)} == {"nisr4", "nisr8"}
