"""Recherche dans les manuels CNP (cahier des charges, section 12, point 3).

Filtre : niveau ≤ niveau de l'enfant (+ langue si précisée), top-k = 4, seuil de similarité.
Si aucun fragment ne dépasse le seuil, la liste est vide : la génération se fera sans contexte.

Usage :
    .venv\\Scripts\\python -m rag.search "لماذا يطير النسر" --niveau 5 --langue ar
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from rag import config
from rag.index import Embedder, bge_embedder, client

TOP_K = 4
SCORE_THRESHOLD = 0.45  # cosinus bge-m3 ; à calibrer avec l'évaluation recall@4


@dataclass
class Hit:
    score: float
    text: str
    book_title: str
    unit: str
    chapter: str
    grade: str
    subject: str
    page: int
    page_end: int
    chunk_id: str


def build_filter(
    max_grade: int | None, lang: str | None, subject: str | None = None
) -> models.Filter | None:
    must: list[models.FieldCondition] = []
    if max_grade is not None:
        must.append(models.FieldCondition(key="grade_num", range=models.Range(lte=max_grade)))
    if lang:
        must.append(models.FieldCondition(key="lang", match=models.MatchValue(value=lang)))
    if subject:
        must.append(models.FieldCondition(key="subject", match=models.MatchValue(value=subject)))
    return models.Filter(must=must) if must else None


def search(
    query: str,
    max_grade: int | None = None,
    lang: str | None = None,
    subject: str | None = None,
    top_k: int = TOP_K,
    threshold: float = SCORE_THRESHOLD,
    embed: Embedder | None = None,
    qc: QdrantClient | None = None,
) -> list[Hit]:
    embed = embed or bge_embedder()
    qc = qc or client()
    result = qc.query_points(
        config.COLLECTION,
        query=embed([query])[0],
        query_filter=build_filter(max_grade, lang, subject),
        limit=top_k,
        score_threshold=threshold,
        with_payload=True,
    )
    return [
        Hit(
            score=p.score,
            text=p.payload["text"],
            book_title=p.payload["book_title"],
            unit=p.payload["unit"],
            chapter=p.payload["chapter"],
            grade=p.payload["grade"],
            subject=p.payload["subject"],
            page=p.payload["page"],
            page_end=p.payload["page_end"],
            chunk_id=p.payload["chunk_id"],
        )
        for p in result.points
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recherche dans les manuels CNP indexés.")
    parser.add_argument("question")
    parser.add_argument("--niveau", type=int, help="niveau de l'enfant (1 à 9) : filtre ≤")
    parser.add_argument("--langue", choices=["ar", "fr", "en"])
    parser.add_argument("--matiere", help="dossier de matière, ex. 03_eveil_scientifique")
    parser.add_argument("-k", type=int, default=TOP_K)
    parser.add_argument("--seuil", type=float, default=SCORE_THRESHOLD)
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    hits = search(args.question, args.niveau, args.langue, args.matiere, args.k, args.seuil)
    if not hits:
        print("Aucun fragment au-dessus du seuil : réponse sans contexte.")
    for i, h in enumerate(hits, 1):
        pages = f"p.{h.page}" + (f"-{h.page_end}" if h.page_end != h.page else "")
        print(f"\n#{i}  score={h.score:.3f}  {h.grade} · {h.subject} · {h.book_title} · {pages}")
        if h.chapter:
            print(f"    leçon : {h.chapter}")
        print("    " + h.text[:400].replace("\n", " ") + ("…" if len(h.text) > 400 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
