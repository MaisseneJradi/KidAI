"""Pipeline d'ingestion des manuels CNP : extraction -> découpage -> index Qdrant.

Chaque étape reprend là où elle s'est arrêtée ; on peut traiter le corpus par lots.

Exemples (depuis la racine du dépôt) :
    .venv\\Scripts\\python -m rag.ingest --niveau 4 --niveau 5 --niveau 6 --matiere 03
    .venv\\Scripts\\python -m rag.ingest                       # tout le corpus
    .venv\\Scripts\\python -m rag.ingest --etapes chunk,index  # sans refaire l'extraction
    .venv\\Scripts\\python -m rag.ingest --reconstruire        # vide la collection puis réindexe
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from dataclasses import asdict

from rag import config
from rag.chunk import Chunk, bge_token_counter, chunk_document
from rag.extract import Document, extract_document, load_documents, read_pages

# rag.index (qdrant-client, torch) n'est importé qu'à l'étape « index » : l'extraction et le
# découpage tournent sans les dépendances lourdes.

ETAPES = ("extract", "chunk", "index")


def select(
    docs: list[Document], grades: list[int] | None, subjects: list[str] | None, category: str | None
) -> list[Document]:
    out = []
    for d in docs:
        if grades and config.grade_number(d.grade) not in grades:
            continue
        if subjects and not any(d.subject.startswith(s) for s in subjects):
            continue
        if category and d.category != category:
            continue
        out.append(d)
    return out


def chunks_path(doc: Document):
    return config.CHUNKS_DIR / f"{doc.doc_id}.jsonl"


def write_chunks(doc: Document, chunks: list[Chunk]) -> None:
    out = chunks_path(doc)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def read_chunks(doc: Document) -> list[Chunk]:
    with chunks_path(doc).open(encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--niveau", type=int, action="append", help="0 à 9 ; répétable")
    parser.add_argument("--matiere", action="append", help="code ou dossier, ex. 03 ; répétable")
    parser.add_argument("--categorie", choices=["eleve", "guide_enseignant"])
    parser.add_argument("--etapes", default=",".join(ETAPES), help="extract,chunk,index")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 4))
    parser.add_argument("--reconstruire", action="store_true", help="recrée la collection Qdrant")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    etapes = [e.strip() for e in args.etapes.split(",")]
    unknown = set(etapes) - set(ETAPES)
    if unknown:
        parser.error(f"étapes inconnues : {', '.join(sorted(unknown))}")

    docs = select(load_documents(), args.niveau, args.matiere, args.categorie)
    print(f"{len(docs)} PDF sélectionnés — étapes : {', '.join(etapes)}")
    t0 = time.monotonic()

    if "extract" in etapes:
        print("\n== Extraction du texte (pdftotext / OCR Tesseract) ==")
        totals: Counter[str] = Counter()
        for i, doc in enumerate(docs, 1):
            print(f"[{i}/{len(docs)}] {doc.grade}/{doc.subject}/{doc.category} · {doc.title}")
            totals.update(extract_document(doc, args.workers))
        print(f"Pages : {dict(totals)}  ({time.monotonic() - t0:.0f} s)")

    if "chunk" in etapes:
        print("\n== Découpage par leçon ==")
        count = bge_token_counter()
        n_chunks = 0
        for doc in docs:
            chunks = chunk_document(doc, read_pages(doc), count)
            write_chunks(doc, chunks)
            n_chunks += len(chunks)
        print(f"{n_chunks} fragments écrits dans {config.CHUNKS_DIR}")

    if "index" in etapes:
        print("\n== Embeddings bge-m3 + index Qdrant ==")
        from rag.index import bge_embedder, client, ensure_collection, index_chunks

        qc = client()
        ensure_collection(qc, recreate=args.reconstruire)
        embed = bge_embedder()
        added = 0
        for i, doc in enumerate(docs, 1):
            print(f"[{i}/{len(docs)}] {doc.doc_id} · {doc.title}")
            added += index_chunks(read_chunks(doc), embed, qc, progress=lambda _m: None)
        total = qc.count(config.COLLECTION).count
        print(f"{added} fragments ajoutés — collection « {config.COLLECTION} » : {total} fragments")

    print(f"\nTerminé en {time.monotonic() - t0:.0f} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
