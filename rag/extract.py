"""Extraction du texte des PDF CNP, page par page : pdftotext si le texte est propre, sinon OCR.

Sortie : data/processed/cnp/pages/<doc_id>.jsonl — une ligne par page :
    {"page": 12, "method": "pdftotext" | "ocr", "text": "..."}
Reprise : un PDF dont le fichier de sortie est complet n'est pas retraité.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from rag import config
from rag.text_quality import is_usable

# Une seule tâche Tesseract par processus : on parallélise par pages, pas dans Tesseract.
_OCR_ENV = {**os.environ, "OMP_THREAD_LIMIT": "1"}


@dataclass(frozen=True)
class Document:
    """Un PDF du corpus, décrit par le manifeste du téléchargement."""

    doc_id: str
    path: Path
    title: str
    grade: str
    subject: str
    category: str
    lang: str
    url: str


def load_documents() -> list[Document]:
    manifest = json.loads(config.MANIFEST.read_text(encoding="utf-8"))
    docs = []
    for entry in manifest.values():
        if entry.get("status") != "ok":
            continue
        title = entry["titre"]
        if entry.get("partie") and entry["partie"] != "Partie 1":
            title += f" ({entry['partie']})"
        docs.append(
            Document(
                doc_id=Path(entry["url"]).stem,  # ex. 103404P00
                path=config.RAW_DIR / entry["fichier"],
                title=title,
                grade=entry["niveau"],
                subject=entry["matiere"],
                category=entry["categorie"],
                lang=config.subject_lang(entry["matiere"]),
                url=entry["url"],
            )
        )
    return sorted(docs, key=lambda d: (d.grade, d.subject, d.category, d.doc_id))


def _run(args: list[str], env: dict[str, str] | None = None) -> str:
    res = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env
    )
    return res.stdout


def page_count(pdf: Path) -> int:
    m = re.search(r"Pages:\s+(\d+)", _run([config.poppler("pdfinfo"), str(pdf)]))
    return int(m.group(1)) if m else 0


def pdftotext_page(pdf: Path, page: int) -> str:
    return _run(
        [config.poppler("pdftotext"), "-f", str(page), "-l", str(page), "-raw", "-enc", "UTF-8",
         str(pdf), "-"]
    )


def ocr_page(pdf: Path, page: int, lang: str) -> str:
    with tempfile.TemporaryDirectory(prefix="kidai_ocr_") as tmp:
        prefix = Path(tmp) / "p"
        subprocess.run(
            [config.poppler("pdftoppm"), "-f", str(page), "-l", str(page), "-r",
             str(config.OCR_DPI), "-gray", "-png", "-singlefile", str(pdf), str(prefix)],
            capture_output=True, check=True,
        )
        return _run(
            [config.tesseract(), str(prefix) + ".png", "stdout", "-l",
             config.TESSERACT_LANG.get(lang, "ara"), "--psm", "3"],
            env=_OCR_ENV,
        )


def extract_page(doc: Document, page: int) -> dict:
    text = pdftotext_page(doc.path, page)
    if is_usable(text, doc.lang):
        return {"page": page, "method": "pdftotext", "text": text}
    return {"page": page, "method": "ocr", "text": ocr_page(doc.path, page, doc.lang)}


def output_path(doc: Document) -> Path:
    return config.PAGES_DIR / f"{doc.doc_id}.jsonl"


def is_done(doc: Document, n_pages: int) -> bool:
    out = output_path(doc)
    if not out.exists():
        return False
    with out.open(encoding="utf-8") as f:
        return sum(1 for _ in f) == n_pages


def extract_document(
    doc: Document, workers: int, progress: Callable[[str], None] = print
) -> dict[str, int]:
    """Extrait un PDF (pages en parallèle). Renvoie le nombre de pages par méthode."""
    n = page_count(doc.path)
    if is_done(doc, n):
        return {"skipped": n}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pages = list(pool.map(lambda p: extract_page(doc, p), range(1, n + 1)))

    out = output_path(doc)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(page, ensure_ascii=False) + "\n")
    tmp.replace(out)  # écriture atomique : un fichier présent est toujours complet

    stats = {"pdftotext": 0, "ocr": 0}
    for page in pages:
        stats[page["method"]] += 1
    progress(f"    {n} pages : {stats['pdftotext']} pdftotext, {stats['ocr']} OCR")
    return stats


def read_pages(doc: Document) -> list[dict]:
    with output_path(doc).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]
