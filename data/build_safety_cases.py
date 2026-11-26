"""Étape 3 : tire les 20 exemples du test de sécurité (10 sûrs, 10 dangereux ; FR, AR, derja).

Source : split « test » de data/processed (jamais vu à l'entraînement), cas « borderline » exclus.
  - FR et AR : kidai_dataset.parquet, 3 sûrs + 3 dangereux par langue ;
  - derja    : thsab_derja.parquet (T-HSAB, seule source derja), 4 sûrs + 4 dangereux.
Tirage reproductible (graine fixe). Sortie : backend/tests/data/safety_cases.json.

Usage (venv racine) : .\\.venv\\Scripts\\python data\\build_safety_cases.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "backend" / "tests" / "data" / "safety_cases.json"
SEED = 42


def _pick(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df.sample(n, random_state=SEED)


def build() -> list[dict[str, str]]:
    kidai = pd.read_parquet(PROCESSED / "kidai_dataset.parquet")
    kidai = kidai[(kidai.split == "test") & (kidai.question.str.len() < 300)]
    thsab = pd.read_parquet(PROCESSED / "thsab_derja.parquet")
    thsab = thsab[(thsab.split == "test") & thsab.text.str.len().between(15, 200)]

    cases: list[dict[str, str]] = []
    for lang in ("fr", "ar"):
        for harm in ("safe", "unsafe"):
            rows = _pick(kidai[(kidai.lang == lang) & (kidai.ground_truth_harm == harm)], 3)
            cases += [
                {"id": r.id, "lang": lang, "harm": harm, "source": r.source, "text": r.question}
                for r in rows.itertuples()
            ]
    for harm in ("safe", "unsafe"):
        rows = _pick(thsab[thsab.ground_truth_harm == harm], 4)
        cases += [
            {"id": r.id, "lang": "derja", "harm": harm, "source": "thsab", "text": r.text}
            for r in rows.itertuples()
        ]
    return cases


if __name__ == "__main__":
    cases = build()
    assert len(cases) == 20 and sum(c["harm"] == "unsafe" for c in cases) == 10
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(cases)} exemples -> {OUT.relative_to(ROOT)}")
