"""Téléchargement des datasets D1-D6 du cahier des charges (section 9.1) dans data/raw/.

Dépôts GitHub clonés (sans historique) et datasets Hugging Face téléchargés tels quels.
Un dataset déjà présent est laissé intact (--force pour le retélécharger). Les manuels CNP
(D8) ont leur propre script : data/download_cnp.py.

    .venv\\Scripts\\python data\\download.py                 # tout ce qui manque
    .venv\\Scripts\\python data\\download.py --only minorbench
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent / "raw"

# nom -> (type, adresse, fichiers à garder pour Hugging Face). Licences : voir data/README.md.
DATASETS: dict[str, tuple[str, str, list[str] | None]] = {
    "kidbench": ("git", "https://github.com/MichiganNLP/kidbench", None),
    "minorbench": ("hf", "govtech/MinorBench", None),
    "orbench": ("hf", "bench-llm/or-bench", ["*.csv", "README.md"]),
    "safechild": (
        "git", "https://github.com/the-responsible-ai-initiative/safe_child_llm_benchmark", None,
    ),
    "pku_saferlhf": ("hf", "PKU-Alignment/PKU-SafeRLHF", ["data/Alpaca*/*.jsonl", "README.md"]),
    "thsab": (
        "git", "https://github.com/Hala-Mulki/T-HSAB-A-Tunisian-Hate-Speech-and-Abusive-Dataset",
        None,
    ),
}


def present(path: Path) -> bool:
    return path.is_dir() and any(p.name not in {".git", ".cache"} for p in path.iterdir())


def fetch(name: str, force: bool) -> str:
    kind, address, patterns = DATASETS[name]
    dest = RAW / name
    if present(dest) and not force:
        return "déjà présent"
    if dest.exists():
        shutil.rmtree(dest)
    if kind == "git":
        subprocess.run(["git", "clone", "--depth", "1", address, str(dest)], check=True)
    else:
        from huggingface_hub import snapshot_download

        snapshot_download(address, repo_type="dataset", local_dir=dest, allow_patterns=patterns)
    return "téléchargé"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--only", action="append", choices=list(DATASETS))
    parser.add_argument("--force", action="store_true", help="retélécharge même si présent")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    RAW.mkdir(parents=True, exist_ok=True)
    for name in args.only or DATASETS:
        print(f"{name:13} {fetch(name, args.force)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
