"""Assemblage de kidai_dataset.parquet (section 9.2).

- Chaque question (anglais d'origine + traductions validées, ou question synthétique) est
  déclinée à plusieurs âges : une ligne par tranche 6-8 / 9-11 / 12-14 (une question
  synthétique, écrite pour une tranche, n'apparaît qu'à cette tranche).
- Le découpage se fait par question de base (base_id) : toutes les variantes, traductions et
  âges d'une même question vont dans le même split, donc rien du test ne se retrouve en train.
- Le jeu de test : `test_questions` questions de base, stratifiées par source et niveau de
  risque, chacune dans une seule langue et à 2 âges (6-8 et 12-14), car l'action attendue
  peut changer avec l'âge. `expected_action` vient des feuilles d'annotation.
"""

from __future__ import annotations

import math
import random
from typing import Any

import pandas as pd

from prep import config
from prep.annotate import final_actions, translation_fixes

COLUMNS = [
    "id", "question", "lang", "age", "grade", "topic", "source", "ground_truth_harm",
    "expected_action", "split",
    # colonnes en plus de la section 9.2
    "base_id", "qid", "category", "variant", "translated",
]

TEST_LANG_ORDER = ("fr", "ar", "en")


def rng_for(seed: int, *key: object) -> random.Random:
    return random.Random(f"{seed}:" + ":".join(map(str, key)))


def variants(
    base: pd.DataFrame, translations: pd.DataFrame, synthetic: pd.DataFrame
) -> pd.DataFrame:
    """Toutes les questions prêtes à décliner par âge : une ligne par (qid, langue)."""
    meta = ["base_id", "qid", "source", "category", "topic", "ground_truth_harm", "variant"]
    en = base.assign(lang="en", translated=False)
    fixes, rejected = translation_fixes()

    def reviewed(df: pd.DataFrame) -> pd.DataFrame:
        keys = list(zip(df["qid"], df["lang"]))
        df = df.assign(question=[fixes.get(k, q) for k, q in zip(keys, df["question"])])
        return df.loc[[k not in rejected for k in keys]]

    tr = reviewed(translations[translations["ok"]])
    tr = tr[["qid", "lang", "question"]].merge(base[meta], on="qid").assign(translated=True)
    syn = synthetic if "translated" in synthetic else synthetic.assign(translated=False)
    out = pd.concat([en, tr, reviewed(syn)], ignore_index=True)
    return out


def choose_test(var: pd.DataFrame, n_test: int, seed: int) -> list[str]:
    """base_id du test, stratifiés par (source, risque) avec un quota ∝ √taille."""
    groups = var.drop_duplicates("base_id").groupby(["source", "ground_truth_harm"])["base_id"]
    sizes = {k: len(g) for k, g in groups}
    weight = {k: math.sqrt(s) for k, s in sizes.items()}
    total = sum(weight.values())
    quota = {k: min(sizes[k], max(2, round(n_test * w / total))) for k, w in weight.items()}
    # Ajuste les arrondis pour tomber juste : on retire au plus gros quota, on ajoute au groupe
    # le moins servi qui a encore des questions.
    while sum(quota.values()) > n_test:
        k = max(quota, key=lambda x: quota[x])
        quota[k] -= 1
    while sum(quota.values()) < n_test and any(quota[k] < sizes[k] for k in quota):
        k = min((k for k in quota if quota[k] < sizes[k]), key=lambda x: quota[x] / weight[x])
        quota[k] += 1
    chosen: list[str] = []
    for k, g in groups:
        ids = sorted(g)
        rng_for(seed, "test", *k).shuffle(ids)
        chosen += ids[: quota[k]]
    return sorted(chosen)


def assign_splits(var: pd.DataFrame, test_ids: set[str], val_fraction: float, seed: int
                  ) -> dict[str, str]:
    split: dict[str, str] = {b: "test" for b in test_ids}
    rest = var[~var["base_id"].isin(test_ids)].drop_duplicates("base_id")
    for source, g in rest.groupby("source"):
        ids = sorted(g["base_id"])
        rng_for(seed, "val", source).shuffle(ids)
        k = round(len(ids) * val_fraction)
        split.update({b: "val" for b in ids[:k]})
        split.update({b: "train" for b in ids[k:]})
    return split


def _row(v: Any, age: int, split: str) -> dict[str, Any]:
    return {
        "id": f"{v.qid}_{v.lang}_{age:02d}", "question": v.question, "lang": v.lang, "age": age,
        "grade": config.grade_of(age), "topic": v.topic, "source": v.source,
        "ground_truth_harm": v.ground_truth_harm, "expected_action": None, "split": split,
        "base_id": v.base_id, "qid": v.qid, "category": v.category, "variant": v.variant,
        "translated": bool(v.translated),
    }


def build(
    base: pd.DataFrame, translations: pd.DataFrame, synthetic: pd.DataFrame,
    params: dict[str, Any], actions: dict[str, str] | None = None,
) -> pd.DataFrame:
    seed, p = params["seed"], params["build"]
    var = variants(base, translations, synthetic)
    test_ids = set(choose_test(var, p["test_questions"], seed))
    split = assign_splits(var, test_ids, p["val_fraction"], seed)

    rows: list[dict[str, Any]] = []
    for v in var[~var["base_id"].isin(test_ids)].itertuples():
        rng = rng_for(seed, "age", v.qid, v.lang)
        if v.source == "synthetic":
            bands = [(int(v.band_lo), int(v.band_hi))]
        else:
            bands = list(config.AGE_BANDS)
        for lo, hi in bands:
            rows.append(_row(v, rng.randint(lo, hi), split[v.base_id]))

    # Test : une variante et une langue par question, aux âges 6-8 et 12-14.
    for i, base_id in enumerate(sorted(test_ids)):
        cand = var[var["base_id"] == base_id]
        rng = rng_for(seed, "test-row", base_id)
        langs = set(cand["lang"])
        order = TEST_LANG_ORDER[i % 3 :] + TEST_LANG_ORDER[: i % 3]
        lang = next((lang for lang in order if lang in langs), sorted(langs)[0])
        options = cand[cand["lang"] == lang].sort_values("qid")
        v = next(options.iloc[[rng.randrange(len(options))]].itertuples())
        if v.source == "synthetic":
            bands = [(int(v.band_lo), int(v.band_hi))]
        else:
            bands = [config.AGE_BANDS[0], config.AGE_BANDS[2]]
        for lo, hi in bands:
            rows.append(_row(v, rng.randint(lo, hi), "test"))

    df = pd.DataFrame(rows, columns=COLUMNS)
    actions = final_actions() if actions is None else actions
    df.loc[df["split"] == "test", "expected_action"] = df["id"].map(actions)
    df = df.sort_values(["split", "id"]).reset_index(drop=True)
    df["age"] = df["age"].astype("int8")
    validate(df)
    return df


def validate(df: pd.DataFrame) -> None:
    """Contrôles de la section 9.2 ; lève une erreur au moindre écart."""
    assert list(df.columns) == COLUMNS, "colonnes inattendues"
    assert df["id"].is_unique, "id en double"
    assert df["lang"].isin(config.LANGS).all()
    assert df["source"].isin(config.SOURCES).all()
    assert df["ground_truth_harm"].isin(config.HARMS).all()
    assert df["split"].isin(config.SPLITS).all()
    assert df["topic"].isin(config.TOPICS).all()
    assert df["age"].between(6, 14).all()
    assert (df["question"].str.len() > 0).all()
    acts = df["expected_action"].dropna()
    assert acts.isin(config.ACTIONS).all()
    assert df.loc[acts.index, "split"].eq("test").all(), "action attendue hors du test"
    per_base = df.groupby("base_id")["split"].nunique()
    assert (per_base == 1).all(), f"fuite entre splits : {list(per_base[per_base > 1].index)[:5]}"
