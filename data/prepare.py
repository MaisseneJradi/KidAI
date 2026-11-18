"""Pipeline du dataset KidAI (étape 4). Chaque étape est aussi une étape de dvc.yaml.

Depuis la racine du dépôt :
    .venv\\Scripts\\python data\\prepare.py normalize    # D1-D6 bruts -> format commun
    .venv\\Scripts\\python data\\prepare.py translate    # FR / AR avec Ollama (reprise auto)
    .venv\\Scripts\\python data\\prepare.py synthetic    # D9 : questions générées
    .venv\\Scripts\\python data\\prepare.py build        # âges, splits, annotations -> parquet
    .venv\\Scripts\\python data\\prepare.py stats        # rapport statistique
    .venv\\Scripts\\python data\\prepare.py annotate     # feuilles d'annotation + kappa
ou simplement : dvc repro
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from prep import annotate, build, config, sources, stats, synthetic, translate
from prep.llm import ChatJson, ollama_chat_json


def _chat(model: str, params: dict) -> ChatJson:
    return ollama_chat_json(model, params["translate"].get("ollama_options", {}).get(model))


def normalize(params: dict) -> None:
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    base = sources.load_all(config.RAW, params)
    base.to_parquet(config.BASE_EN, index=False)
    print(f"{len(base)} questions anglaises ({base['base_id'].nunique()} de base) -> {config.BASE_EN}")
    print(base.groupby(["source", "ground_truth_harm"]).size().to_string())
    pku = sources.load_pku(config.RAW)
    pku.to_parquet(config.PKU, index=False)
    print(f"{len(pku)} paires PKU-SafeRLHF -> {config.PKU}")
    thsab = sources.load_thsab(config.RAW, params["seed"])
    thsab.to_parquet(config.THSAB, index=False)
    print(f"{len(thsab)} commentaires T-HSAB (derja) -> {config.THSAB}")


def run_translate(params: dict) -> None:
    p = params["translate"]
    base = pd.read_parquet(config.BASE_EN)
    models = {lang: p["models"][lang] for lang in p["langs"]}
    chats = {lang: _chat(m, params) for lang, m in models.items()}
    df = translate.run(base, p["langs"], chats, models, p["batch_size"])
    df.to_parquet(config.TRANSLATIONS, index=False)
    print(f"{int(df['ok'].sum())} traductions valides, {int((~df['ok']).sum())} rejetées")


def run_synthetic(params: dict) -> None:
    p, t = params["synthetic"], params["translate"]
    generated = synthetic.run(p["langs"], _chat(p["model"], params), p["model"], p["per_cell"])
    print(f"{len(generated)} questions générées ({', '.join(p['langs'])})")
    models = {lang: t["models"][lang] for lang in p["translate_to"]}
    chats = {lang: _chat(m, params) for lang, m in models.items()}
    tr = translate.run(generated, p["translate_to"], chats, models, t["batch_size"],
                       config.SYNTHETIC_TR_CACHE)
    df = synthetic.with_translations(generated, tr)
    df.to_parquet(config.SYNTHETIC, index=False)
    print(f"{len(df)} lignes synthétiques (avec traductions) -> {config.SYNTHETIC}")


def run_build(params: dict) -> None:
    df = build.build(
        pd.read_parquet(config.BASE_EN),
        pd.read_parquet(config.TRANSLATIONS),
        pd.read_parquet(config.SYNTHETIC),
        params,
    )
    df.to_parquet(config.DATASET, index=False)
    print(f"{len(df)} lignes -> {config.DATASET}")
    print(df.groupby("split").size().to_string())


def run_stats(params: dict) -> None:
    extra = {
        "T-HSAB (derja, fichier séparé)": pd.read_parquet(config.THSAB)[["label", "split"]],
        "PKU-SafeRLHF (préférences, fichier séparé)": pd.read_parquet(
            config.PKU, columns=["generator", "split"]
        ),
    }
    metrics = stats.write(pd.read_parquet(config.DATASET), extra, config.STATS_MD, config.STATS_JSON)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def run_annotate(params: dict) -> None:
    dataset = pd.read_parquet(config.DATASET)
    for path in annotate.export_test_sheets(dataset, pd.read_parquet(config.BASE_EN)):
        print(f"feuille écrite : {path}")
    path = annotate.export_translation_review(
        pd.read_parquet(config.TRANSLATIONS), pd.read_parquet(config.BASE_EN),
        pd.read_parquet(config.SYNTHETIC), 0.10, params["seed"],
    )
    if path:
        print(f"feuille écrite : {path}")
    print(json.dumps(annotate.agreement_report(), ensure_ascii=False, indent=2))


STAGES = {
    "normalize": normalize,
    "translate": run_translate,
    "synthetic": run_synthetic,
    "build": run_build,
    "stats": run_stats,
    "annotate": run_annotate,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("etape", choices=list(STAGES))
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    STAGES[args.etape](config.load_params())
    return 0


if __name__ == "__main__":
    sys.exit(main())
