"""Téléchargement des manuels du CNP (cycle أساسي), élève et guide de l'enseignant.

Source : moteur de recherche https://cnp.com.tn/CNP1/web/arabic/biblio/man-eleves.jsp
(robots.txt : tout autorisé). Usage strictement académique : les manuels ne doivent pas être
redistribués (cahier des charges, section 9) ; data/raw/ n'est jamais commité.

Politesse : une seule requête à la fois, pause de 3 s entre chaque requête (recherche ou PDF).

Exemples :
    .venv\\Scripts\\python data\\download_cnp.py --dry-run              # inventaire, rien n'est téléchargé
    .venv\\Scripts\\python data\\download_cnp.py --niveau 1             # un seul niveau
    .venv\\Scripts\\python data\\download_cnp.py                        # tout le cycle de base
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import ssl
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests
import truststore
from pypdf import PdfReader
from requests.adapters import HTTPAdapter

BASE_URL = "https://cnp.com.tn/CNP1/web/arabic/biblio/"
SEARCH_URL = BASE_URL + "resultat_man.jsp"
USER_AGENT = "KidAI academic project - FST"
DELAY_S = 3.0
MAX_RETRIES = 3
TIMEOUT_S = 60

OUT_DIR = Path(__file__).resolve().parent / "raw" / "cnp"
MANIFEST = OUT_DIR / "manifest.json"
CATALOGUE = OUT_DIR / "catalogue.csv"

CYCLE = ("1", "أساسي", "base")

# Codes du formulaire CNP -> nom de dossier (même convention que le champ `grade` de l'app).
NIVEAUX = {
    "0": "0_preparatoire",
    "1": "1e_annee",
    "2": "2e_annee",
    "3": "3e_annee",
    "4": "4e_annee",
    "5": "5e_annee",
    "6": "6e_annee",
    "7": "7e_annee",
    "8": "8e_annee",
    "9": "9e_annee",
}

# Code -> (dossier, langue d'enseignement par défaut). La langue est affinée avec le titre.
MATIERES = {
    "01": ("01_arabe", "ar"),
    "02": ("02_mathematiques", "ar"),
    "03": ("03_eveil_scientifique", "ar"),
    "05": ("05_svt", "ar"),
    "06": ("06_geographie", "ar"),
    "07": ("07_histoire", "ar"),
    "08": ("08_education_art_tech_musique", "ar"),
    "09": ("09_jeux_loisirs", "ar"),
    "10": ("10_philosophie", "ar"),
    "11": ("11_sociales_islamique_civique", "ar"),
    "12": ("12_education_physique", "ar"),
    "21": ("21_francais", "fr"),
    "22": ("22_mathematique_fr", "fr"),
    "23": ("23_physique", "fr"),
    "24": ("24_chimie", "fr"),
    "25": ("25_sciences_naturelles", "fr"),
    "28": ("28_technologie", "fr"),
    "29": ("29_economie_gestion", "fr"),
    "33": ("33_informatique", "fr"),
    "41": ("41_anglais", "en"),
    "61": ("61_allemand", "de"),
    "81": ("81_italien", "it"),
    "91": ("91_espagnol", "es"),
}

CATEGORIES = {"eleve": "eleve", "enseignant": "guide_enseignant"}

# pypdf signale des objets mal formés (fréquents dans ces PDF) sans gêner le comptage des pages.
logging.getLogger("pypdf").setLevel(logging.ERROR)

ARABIC = re.compile(r"[؀-ۿ]")
FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class Document:
    url: str
    code: str
    titre: str
    partie: str
    niveau: str
    matiere: str
    categorie: str
    langue: str
    fichier: str


# --------------------------------------------------------------------------- recherche


class _ResultTable(HTMLParser):
    """Lignes du tableau de résultats : [code, titre, liens]. Gère les rowspan (plusieurs parties)."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[list[str], list[tuple[str, str]]]] = []
        self._row: tuple[list[str], list[tuple[str, str]]] | None = None
        self._td = False
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "tr" and a.get("class") == "tr_content":
            self._row = ([], [])
        elif self._row is not None and tag == "td":
            self._td = True
            self._row[0].append("")
        elif self._row is not None and tag == "a" and a.get("href"):
            self._href = a["href"]
            self._row[1].append((a["href"] or "", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "td":
            self._td = False
        elif tag == "a":
            self._href = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._row is None or not self._td:
            return
        if self._href is not None:
            href, label = self._row[1][-1]
            self._row[1][-1] = (href, label + data)
        else:
            self._row[0][-1] += data


def parse_results(html: str) -> list[tuple[str, str, str, str]]:
    """Renvoie (code, titre, libellé de la partie, URL absolue du PDF)."""
    parser = _ResultTable()
    parser.feed(html)
    out: list[tuple[str, str, str, str]] = []
    code = titre = ""
    for cells, links in parser.rows:
        texts = [c.strip() for c in cells]
        if len(texts) >= 3:  # ligne complète ; sinon continuation d'un rowspan
            code, titre = texts[0], texts[1]
        for href, label in links:
            if href.lower().endswith(".pdf"):
                out.append((code, titre, label.strip(), urljoin(SEARCH_URL, href)))
    return out


def safe_name(text: str, max_len: int = 90) -> str:
    name = FORBIDDEN.sub("_", text).strip().strip(".")
    name = re.sub(r"\s+", " ", name)
    return name[:max_len].rstrip() or "sans_titre"


def detect_lang(titre: str, default: str) -> str:
    return "ar" if ARABIC.search(titre) else default


class _SystemTrustAdapter(HTTPAdapter):
    """Vérifie le TLS avec le magasin de certificats du système plutôt qu'avec certifi.

    Le serveur du CNP n'envoie pas son certificat intermédiaire : certifi échoue, alors que le
    système (Windows, macOS) sait le compléter. La vérification reste active (jamais verify=False).
    """

    def init_poolmanager(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return super().init_poolmanager(*args, **kwargs)


class Client:
    """Session HTTP qui garantit la pause entre deux requêtes."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.mount("https://", _SystemTrustAdapter())
        self.session.headers["User-Agent"] = USER_AGENT
        self._last = 0.0

    def _wait(self) -> None:
        pause = DELAY_S - (time.monotonic() - self._last)
        if pause > 0:
            time.sleep(pause)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        self._wait()
        try:
            res = self.session.request(method, url, timeout=TIMEOUT_S, **kwargs)
            res.raise_for_status()
            return res
        finally:
            self._last = time.monotonic()


def with_retries(action, what: str):
    """Exécute `action`, avec MAX_RETRIES nouvelles tentatives en cas d'erreur."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return action()
        except (requests.RequestException, ValueError) as exc:
            if attempt == MAX_RETRIES:
                raise
            print(f"    ! {what} : {exc} — nouvelle tentative {attempt + 1}/{MAX_RETRIES}")
            time.sleep(DELAY_S * (attempt + 1))
    raise AssertionError("inaccessible")


def discover(client: Client, niveaux: list[str]) -> list[Document]:
    docs: dict[str, Document] = {}
    combos = [(n, m, c) for n in niveaux for m in MATIERES for c in CATEGORIES]
    for i, (niveau, matiere, cat) in enumerate(combos, 1):
        form = {"CYCLE": CYCLE[0], "CLASSE": niveau, "MATIERE": matiere, "type": cat}
        what = f"recherche niveau={niveau} matiere={matiere} type={cat}"
        try:
            res = with_retries(
                lambda form=form: client.request(
                    "POST", SEARCH_URL, data=form, headers={"Referer": BASE_URL + "man-eleves.jsp"}
                ),
                what,
            )
        except requests.RequestException as exc:
            print(f"[{i}/{len(combos)}] {what} : ÉCHEC ({exc})")
            continue
        res.encoding = "utf-8"
        found = parse_results(res.text)
        print(f"[{i}/{len(combos)}] {what} : {len(found)} PDF")

        mat_dir, mat_lang = MATIERES[matiere]
        parts_per_code = Counter(code for code, *_ in found)
        for code, titre, partie, url in found:
            if url in docs:  # même PDF listé dans plusieurs recherches
                continue
            stem = f"{safe_name(titre)} ({code})"
            if parts_per_code[code] > 1:
                stem += f" - {safe_name(partie, 20)}"
            rel = Path(NIVEAUX[niveau], mat_dir, CATEGORIES[cat], stem + ".pdf")
            docs[url] = Document(
                url=url,
                code=code,
                titre=titre,
                partie=partie,
                niveau=NIVEAUX[niveau],
                matiere=mat_dir,
                categorie=CATEGORIES[cat],
                langue=detect_lang(titre, mat_lang),
                fichier=rel.as_posix(),
            )
    return list(docs.values())


# --------------------------------------------------------------------------- téléchargement


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_pages(path: Path) -> int | None:
    try:
        return len(PdfReader(path).pages)
    except Exception:  # noqa: BLE001 — PDF illisible : on ne bloque pas le catalogue
        return None


def load_manifest() -> dict[str, dict]:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict[str, dict]) -> None:
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(MANIFEST)


def is_valid(entry: dict | None) -> bool:
    """Le fichier est présent et correspond au manifeste (taille + SHA-256)."""
    if not entry or entry.get("status") != "ok":
        return False
    path = OUT_DIR / entry["fichier"]
    return path.is_file() and path.stat().st_size == entry["taille"] and sha256(path) == entry["sha256"]


def download(client: Client, doc: Document) -> dict:
    dest = OUT_DIR / doc.fichier
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    def fetch() -> None:
        res = client.request("GET", doc.url, stream=True, headers={"Referer": SEARCH_URL})
        with part.open("wb") as f:
            for chunk in res.iter_content(1 << 16):
                f.write(chunk)
        with part.open("rb") as f:
            if f.read(5) != b"%PDF-":
                raise ValueError("le fichier reçu n'est pas un PDF")

    with_retries(fetch, f"téléchargement {doc.url}")
    part.replace(dest)
    return {
        **asdict(doc),
        "status": "ok",
        "sha256": sha256(dest),
        "taille": dest.stat().st_size,
        "pages": count_pages(dest),
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def write_catalogue(manifest: dict[str, dict]) -> None:
    columns = ["titre", "cycle", "niveau", "matiere", "langue", "categorie", "url", "fichier", "pages"]
    rows = sorted(
        (e for e in manifest.values() if e.get("status") == "ok"),
        key=lambda e: (e["niveau"], e["matiere"], e["categorie"], e["fichier"]),
    )
    # utf-8-sig : l'arabe s'affiche correctement à l'ouverture dans Excel.
    with CATALOGUE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for e in rows:
            titre = e["titre"] + (f" ({e['partie']})" if e["partie"] not in ("", "Partie 1") else "")
            writer.writerow({**{k: e.get(k) for k in columns}, "titre": titre, "cycle": CYCLE[2]})


# --------------------------------------------------------------------------- CLI


def print_inventory(docs: list[Document]) -> None:
    counts = Counter((d.niveau, d.matiere, d.categorie) for d in docs)
    print(f"\n{'niveau':<16}{'matiere':<34}{'categorie':<18}PDF")
    for (niveau, matiere, cat), n in sorted(counts.items()):
        print(f"{niveau:<16}{matiere:<34}{cat:<18}{n}")
    print(f"\nTotal : {len(docs)} PDF ({len({d.code for d in docs})} manuels distincts)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="liste les PDF sans les télécharger")
    parser.add_argument(
        "--niveau",
        action="append",
        choices=list(NIVEAUX),
        help="niveau à traiter (0 = préparatoire, 1 à 9) ; répétable. Par défaut : tous",
    )
    args = parser.parse_args(argv)
    niveaux = args.niveau or list(NIVEAUX)
    if hasattr(sys.stdout, "reconfigure"):  # titres arabes dans la console Windows
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    client = Client()
    print(f"Recherche des PDF — cycle {CYCLE[1]}, niveaux {', '.join(niveaux)}")
    docs = discover(client, niveaux)
    print_inventory(docs)
    if args.dry_run:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    done = skipped = failed = 0
    for i, doc in enumerate(docs, 1):
        if is_valid(manifest.get(doc.url)):
            skipped += 1
            continue
        print(f"[{i}/{len(docs)}] {doc.fichier}")
        try:
            manifest[doc.url] = download(client, doc)
            done += 1
        except (requests.RequestException, ValueError, OSError) as exc:
            failed += 1
            manifest[doc.url] = {
                **asdict(doc),
                "status": "failed",
                "error": str(exc),
                "date": datetime.now(UTC).isoformat(timespec="seconds"),
            }
            print(f"    ✗ échec définitif : {exc}")
        save_manifest(manifest)

    write_catalogue(manifest)
    print(
        f"\nTerminé : {done} téléchargés, {skipped} déjà présents, {failed} en échec "
        f"(voir {MANIFEST.relative_to(OUT_DIR.parent.parent)})."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
