"""Rapport statistique du dataset : répartition par source, âge, langue, risque, split."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from prep import config
from prep.annotate import agreement_report, review_report


def _table(df: pd.DataFrame, index: str, columns: str = "split") -> str:
    t = pd.crosstab(df[index], df[columns], margins=True, margins_name="total")
    head = f"| {index} | " + " | ".join(map(str, t.columns)) + " |"
    sep = "|---|" + "---:|" * len(t.columns)
    body = [f"| {i} | " + " | ".join(f"{v:,}".replace(",", " ") for v in row) + " |"
            for i, row in zip(t.index, t.values)]
    return "\n".join([head, sep, *body])


def report(df: pd.DataFrame, extra: dict[str, pd.DataFrame]) -> tuple[str, dict[str, Any]]:
    band = df["age"].map(lambda a: "{}-{}".format(*config.AGE_BANDS[config.band_of(a)]))
    df = df.assign(tranche=band, action=df["expected_action"].fillna("—"))
    test = df[df["split"] == "test"]
    agreement = agreement_report()
    review = review_report()
    metrics: dict[str, Any] = {
        "lignes": len(df),
        "questions_de_base": int(df["base_id"].nunique()),
        **{f"lignes_{s}": int((df["split"] == s).sum()) for s in config.SPLITS},
        "test_annote": int(test["expected_action"].notna().sum()),
        "test_total": len(test),
        "kappa": agreement.get("kappa"),
        "traductions_relues": review.get("relues", 0),
    }
    parts = [
        "# Dataset KidAI — statistiques",
        "",
        "Fichier : `data/processed/kidai_dataset.parquet` (régénéré par `dvc repro`).",
        "",
        f"- **{metrics['lignes']:,}** lignes, **{metrics['questions_de_base']:,}** questions de "
        "base".replace(",", " "),
        f"- test : {metrics['test_annote']} / {metrics['test_total']} lignes annotées",
        f"- accord des annotateurs : {json.dumps(agreement, ensure_ascii=False)}",
        f"- relecture des traductions : {json.dumps(review, ensure_ascii=False)}",
        "",
        "## Par source", "", _table(df, "source"), "",
        "## Par langue", "", _table(df, "lang"), "",
        "## Par tranche d'âge", "", _table(df, "tranche"), "",
        "## Par niveau de risque (dérivé de la source)", "", _table(df, "ground_truth_harm"), "",
        "## Par sujet", "", _table(df, "topic"), "",
        "## Risque × source (questions de base)", "",
        _table(df.drop_duplicates("base_id"), "source", "ground_truth_harm"), "",
        "## Jeu de test : action attendue × tranche d'âge", "", _table(test, "action", "tranche"),
        "",
    ]
    for name, side in extra.items():
        parts += [f"## {name}", "", _table(side, side.columns[0], "split"), ""]
    return "\n".join(parts), metrics


def write(df: pd.DataFrame, extra: dict[str, pd.DataFrame], md: Path, js: Path) -> dict[str, Any]:
    text, metrics = report(df, extra)
    md.write_text(text, encoding="utf-8")
    js.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics
