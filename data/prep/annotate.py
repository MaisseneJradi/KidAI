"""Annotation humaine : jeu de test (action attendue, 2 annotateurs + arbitrage, kappa de
Cohen) et relecture d'un échantillon de 10 % des traductions.

Les feuilles sont des CSV (UTF-8 avec BOM, lisibles dans Excel) dans data/annotation/.
Une feuille déjà commencée n'est jamais écrasée.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from prep import config

SHEET_A = "test_annotateur_A.csv"
SHEET_B = "test_annotateur_B.csv"
SHEET_ARB = "test_arbitrage.csv"
SHEET_TR = "translation_review.csv"

SHEET_COLUMNS = ["id", "age", "grade", "lang", "question", "question_en", "action", "commentaire"]


def read_sheet(path: Path) -> pd.DataFrame:
    # Séparateur détecté : Excel en français enregistre les CSV avec « ; » au lieu de « , ».
    return pd.read_csv(
        path, dtype=str, keep_default_na=False, encoding="utf-8-sig", sep=None, engine="python"
    )


def write_sheet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_actions(path: Path) -> dict[str, str]:
    """id -> action, pour les lignes remplies ; une action inconnue est une erreur."""
    if not path.exists():
        return {}
    df = read_sheet(path)
    out: dict[str, str] = {}
    for r in df.itertuples():
        action = str(r.action).strip().upper().replace(" ", "_").replace("-", "_")
        if not action:
            continue
        if action not in config.ACTIONS:
            raise ValueError(f"{path.name}, {r.id} : action inconnue « {r.action} »")
        out[str(r.id)] = action
    return out


def cohen_kappa(a: list[str], b: list[str]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("il faut deux listes de même longueur, non vides")
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def resolve(
    a: dict[str, str], b: dict[str, str], arbitrage: dict[str, str]
) -> dict[str, str]:
    """Action finale : accord des deux annotateurs, sinon décision du 3e."""
    final = {i: a[i] for i in a.keys() & b.keys() if a[i] == b[i]}
    final.update({i: act for i, act in arbitrage.items() if i in a and i in b and a[i] != b[i]})
    return final


def final_actions(folder: Path = config.ANNOTATION) -> dict[str, str]:
    return resolve(
        read_actions(folder / SHEET_A),
        read_actions(folder / SHEET_B),
        read_actions(folder / SHEET_ARB),
    )


def export_test_sheets(
    dataset: pd.DataFrame, base: pd.DataFrame, folder: Path = config.ANNOTATION
) -> list[Path]:
    """Deux feuilles identiques et vierges, une par annotateur. `base` donne l'original anglais
    des questions traduites (vide pour les questions déjà en anglais ou synthétiques)."""
    test = dataset[dataset["split"] == "test"].sort_values("id")
    english = dict(zip(base["qid"], base["question"]))
    question_en = [english.get(q, "") if t else "" for q, t in zip(test["qid"], test["translated"])]
    sheet = test.assign(question_en=question_en, action="", commentaire="")[SHEET_COLUMNS]
    written = []
    for name in (SHEET_A, SHEET_B):
        path = folder / name
        if path.exists() and read_sheet(path)["action"].str.strip().ne("").any():
            print(f"{name} déjà commencée : non modifiée")
            continue
        write_sheet(sheet, path)
        written.append(path)
    return written


def agreement_report(folder: Path = config.ANNOTATION) -> dict[str, object]:
    """Kappa sur les lignes annotées par A et B ; écrit la feuille d'arbitrage des désaccords."""
    a, b = read_actions(folder / SHEET_A), read_actions(folder / SHEET_B)
    common = sorted(a.keys() & b.keys())
    if not common:
        return {"annotees_A": len(a), "annotees_B": len(b), "communes": 0, "kappa": None}
    kappa = cohen_kappa([a[i] for i in common], [b[i] for i in common])
    disagree = [i for i in common if a[i] != b[i]]

    sheet_a = read_sheet(folder / SHEET_A).set_index("id")
    arb_path = folder / SHEET_ARB
    previous = read_actions(arb_path)
    rows = [
        {"id": i, "age": sheet_a.at[i, "age"], "lang": sheet_a.at[i, "lang"],
         "question": sheet_a.at[i, "question"], "action_A": a[i], "action_B": b[i],
         "action": previous.get(i, "")}
        for i in disagree
    ]
    write_sheet(pd.DataFrame(rows, columns=["id", "age", "lang", "question", "action_A",
                                            "action_B", "action"]), arb_path)
    return {
        "annotees_A": len(a), "annotees_B": len(b), "communes": len(common),
        "accord_brut": round(1 - len(disagree) / len(common), 3), "kappa": round(kappa, 3),
        "desaccords": len(disagree), "arbitres": sum(1 for i in disagree if previous.get(i)),
    }


def export_translation_review(
    translations: pd.DataFrame, base: pd.DataFrame, synthetic: pd.DataFrame, fraction: float,
    seed: int, folder: Path = config.ANNOTATION,
) -> Path | None:
    """Échantillon par langue et source, questions synthétiques comprises (leur original est en
    français, celui des autres en anglais)."""
    path = folder / SHEET_TR
    if path.exists():
        print(f"{SHEET_TR} existe déjà : non modifiée")
        return None
    columns = ["qid", "lang", "question"]
    translated = pd.concat([translations.loc[translations["ok"], columns],
                            synthetic.loc[synthetic["translated"], columns]])
    originals = pd.concat([base[["qid", "source", "question"]],
                           synthetic.loc[~synthetic["translated"], ["qid", "source", "question"]]])
    ok = translated.merge(originals, on="qid", suffixes=("", "_original"))
    sample = ok.groupby(["lang", "source"]).sample(frac=fraction, random_state=seed)
    sheet = pd.DataFrame({
        "qid": sample["qid"], "lang": sample["lang"], "source": sample["source"],
        "original": sample["question_original"], "traduction": sample["question"],
        "correcte": "", "correction": "",
    }).sort_values(["lang", "qid"])
    write_sheet(sheet, path)
    return path


def translation_fixes(folder: Path = config.ANNOTATION) -> tuple[dict[tuple[str, str], str],
                                                                 set[tuple[str, str]]]:
    """(corrections, rejets) issus de la relecture : (qid, lang) -> texte corrigé."""
    path = folder / SHEET_TR
    if not path.exists():
        return {}, set()
    fixes: dict[tuple[str, str], str] = {}
    rejected: set[tuple[str, str]] = set()
    for r in read_sheet(path).itertuples():
        key = (r.qid, r.lang)
        if r.correction.strip():
            fixes[key] = r.correction.strip()
        elif r.correcte.strip().lower() in {"non", "no", "n", "0"}:
            rejected.add(key)
    return fixes, rejected


def review_report(folder: Path = config.ANNOTATION) -> dict[str, object]:
    path = folder / SHEET_TR
    if not path.exists():
        return {"echantillon": 0}
    df = read_sheet(path)
    done = df[df["correcte"].str.strip().ne("") | df["correction"].str.strip().ne("")]
    good = done["correcte"].str.strip().str.lower().isin({"oui", "yes", "o", "1"})
    good &= done["correction"].str.strip().eq("")
    out: dict[str, object] = {"echantillon": len(df), "relues": len(done)}
    for lang, g in done.assign(good=good).groupby("lang"):
        out[f"correctes_{lang}"] = round(float(g["good"].mean()), 3)
    return out
