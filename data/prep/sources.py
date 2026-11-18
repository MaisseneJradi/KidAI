"""Lecture des datasets bruts D1-D6 et correspondance vers le vocabulaire KidAI.

Chaque chargeur renvoie des questions en anglais (langue d'origine) au format commun :
base_id (identifiant de la question, partagé par toutes ses variantes et traductions),
qid (identifiant de la variante), question, source, category (catégorie d'origine), topic,
ground_truth_harm et variant.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

Row = dict[str, Any]

# --- D1 KIDBench (MichiganNLP/kidbench, MIT) ---------------------------------------------
KIDBENCH_TOPIC = {
    "sexual_content_and_boundaries": "sexualite",
    "self-harm_and_mental_health": "emotions",
    "aggression_and_bullying": "violence",
    "moral_reasoning": "morale",
    "physical_health_and_safety": "sante",
    "school_conduct_and_integrity": "ecole",
    "family_peers_and_relationships": "relations",
    "online_safety_and_privacy": "numerique",
    "hate_bias_and_identity_attacks": "discrimination",
    "benign_information_seeking": "curiosite",
}

# --- D2 MinorBench (govtech/MinorBench, MIT) : tout est inadapté aux enfants -------------
MINORBENCH_TOPIC = {
    "Sexual": "sexualite",
    "Hateful": "discrimination",
    "Self-harm": "emotions",
    "Danger": "danger",
    "Substance use": "substances",
    "Profanities": "langage",
}

# --- D3 OR-Bench (bench-llm/or-bench, CC BY 4.0) -----------------------------------------
ORBENCH_TOPIC = {
    "harmful": "danger",
    "unethical": "morale",
    "illegal": "illegal",
    "privacy": "numerique",
    "deception": "morale",
    "violence": "violence",
    "hate": "discrimination",
    "self-harm": "emotions",
    "sexual": "sexualite",
    "harassment": "violence",
}

# --- D4 Safe-Child-LLM (MIT) : questions piégées ; détresse et attachement = borderline ---
SAFECHILD_TOPIC = {
    "Assisting illegal activities": "illegal",
    "Social stereotypes and unfair discrimination": "discrimination",
    "Toxic language (hate speech)": "langage",
    "Compromise privacy by leaking or inferring private information (person/individual)": (
        "numerique"
    ),
    "Adult Content": "sexualite",
    "Mental Health or Overreliance Crisis": "emotions",
    "Judging or advising users to perform unethical or unsafe actions": "morale",
    "Reducing the cost of disinformation campaigns": "numerique",
    "Treat Chatbot as a Human": "relations",
}
SAFECHILD_BORDERLINE = {"Mental Health or Overreliance Crisis", "Treat Chatbot as a Human"}


def normalize_text(text: str) -> str:
    """Espaces, guillemets typographiques et caractères invisibles uniformisés."""
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"')
    text = text.replace("”", '"').replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def dedup_key(text: str) -> str:
    """Clé de doublon : minuscules, sans ponctuation."""
    return re.sub(r"[^\w]+", " ", text.lower()).strip()


def load_kidbench(raw: Path) -> list[Row]:
    rows: list[Row] = []
    single = json.loads(
        (raw / "kidbench/dataset/kidbench/kidbench_single.json").read_text(encoding="utf-8")
    )
    n = 0
    for category, items in single["english"].items():
        harm = "safe" if category == "benign_information_seeking" else "borderline"
        for item in items:
            n += 1
            base_id = f"kb_{n:05d}"
            for variant, suffix in (("without_cues", ""), ("with_cues", "c")):
                if item.get(variant):
                    rows.append(
                        _row(base_id, base_id + suffix, item[variant], "kidbench", category,
                             KIDBENCH_TOPIC[category], harm, variant)
                    )
    # Questions réelles d'enfants partagées par des parents : mélange de bénin et de délicat.
    wild = json.loads(
        (raw / "kidbench/dataset/kidbench/kidbench_wild.json").read_text(encoding="utf-8")
    )
    for i, q in enumerate(wild["reddit_x_shared"], 1):
        base_id = f"kw_{i:05d}"
        rows.append(_row(base_id, base_id, q, "kidbench", "wild", "curiosite", "borderline", "wild"))
    return rows


def load_minorbench(raw: Path) -> list[Row]:
    df = pd.read_csv(raw / "minorbench/test.csv")
    return [
        _row(f"mb_{int(r.PromptID):05d}", f"mb_{int(r.PromptID):05d}", r.Prompt, "minorbench",
             r.Category, MINORBENCH_TOPIC[r.Category], "unsafe", "original")
        for r in df.itertuples()
    ]


def load_orbench(raw: Path, hard_n: int, toxic_n: int, seed: int) -> list[Row]:
    rows: list[Row] = []
    for name, prefix, harm, n in (
        ("or-bench-hard-1k.csv", "oh", "borderline", hard_n),
        ("or-bench-toxic.csv", "ot", "unsafe", toxic_n),
    ):
        df = pd.read_csv(raw / "orbench" / name).reset_index(names="idx")
        # Échantillon stratifié par catégorie, reproductible.
        frac = min(1.0, n / len(df))
        sample = df.groupby("category").sample(frac=frac, random_state=seed)
        sample = sample.sort_values("idx").head(n)
        for r in sample.itertuples():
            base_id = f"{prefix}_{int(r.idx) + 1:05d}"
            rows.append(_row(base_id, base_id, r.prompt, "orbench", r.category,
                             ORBENCH_TOPIC[r.category], harm, "original"))
    return rows


def load_safechild(raw: Path) -> list[Row]:
    rows: list[Row] = []
    for name, prefix in (("6_12_ChildSafeLLM.xlsx", "sc6"), ("13_17_ChildSafeLLM.xlsx", "sc13")):
        df = pd.read_excel(raw / "safechild/assets" / name).rename(columns={"Index": "num"})
        for r in df.itertuples():
            base_id = f"{prefix}_{int(r.num):05d}"
            harm = "borderline" if r.category in SAFECHILD_BORDERLINE else "unsafe"
            rows.append(_row(base_id, base_id, r.query, "safechild", r.category,
                             SAFECHILD_TOPIC[r.category], harm, name.split("_Child")[0]))
    return rows


def load_all(raw: Path, params: dict[str, Any]) -> pd.DataFrame:
    src = params["sources"]
    rows = (
        load_kidbench(raw)
        + load_minorbench(raw)
        + load_orbench(raw, src["orbench_hard_n"], src["orbench_toxic_n"], params["seed"])
        + load_safechild(raw)
    )
    df = pd.DataFrame(rows)
    df = df[df["question"].str.len() > 0]
    # Une question présente dans deux sources (ou deux fois) n'est gardée qu'une fois : sinon
    # elle pourrait se retrouver à la fois en train et en test.
    df["_key"] = df["question"].map(dedup_key)
    df = df.drop_duplicates("_key", keep="first").drop(columns="_key")
    return df.reset_index(drop=True)


def load_pku(raw: Path) -> pd.DataFrame:
    """D5 PKU-SafeRLHF (CC BY-NC 4.0) : paires de réponses notées sécurité / utilité."""
    keep = [
        "prompt", "response_0", "response_1", "is_response_0_safe", "is_response_1_safe",
        "safer_response_id", "better_response_id", "response_0_severity_level",
        "response_1_severity_level",
    ]
    frames = []
    for path in sorted((raw / "pku_saferlhf/data").glob("*/*.jsonl")):
        df = pd.read_json(path, lines=True)
        df = df[[c for c in keep if c in df.columns]]
        df["generator"] = path.parent.name
        df["split"] = path.stem
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_thsab(raw: Path, seed: int) -> pd.DataFrame:
    """D6 T-HSAB : commentaires en derja (normal / abusive / hate) pour tester le risque."""
    df = pd.read_excel(raw / "thsab/T-HSAB Corpus/T-HSAB.xlsx", header=None, names=["text", "label"])
    df["text"] = df["text"].astype(str).map(normalize_text)
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df = df[df["text"].str.len() > 0].drop_duplicates("text").reset_index(drop=True)
    df["ground_truth_harm"] = df["label"].map({"normal": "safe"}).fillna("unsafe")
    df["lang"] = "derja"
    df["id"] = [f"th_{i + 1:05d}" for i in range(len(df))]
    # 80 / 10 / 10, stratifié par label.
    df["split"] = "train"
    for _, g in df.groupby("label"):
        idx = g.sample(frac=1.0, random_state=seed).index
        k = len(idx) // 10
        df.loc[idx[:k], "split"] = "test"
        df.loc[idx[k : 2 * k], "split"] = "val"
    return df[["id", "text", "lang", "label", "ground_truth_harm", "split"]]


def _row(
    base_id: str, qid: str, question: str, source: str, category: str, topic: str, harm: str,
    variant: str,
) -> Row:
    return {
        "base_id": base_id,
        "qid": qid,
        "question": normalize_text(question),
        "source": source,
        "category": category,
        "topic": topic,
        "ground_truth_harm": harm,
        "variant": variant,
    }
