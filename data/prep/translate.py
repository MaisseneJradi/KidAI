"""Traduction des questions anglaises en français et en arabe avec un LLM local (Ollama).

Les traductions sont gardées dans data/cache/translations.jsonl (une ligne par question et
langue) : une relance ne traduit que ce qui manque. Chaque traduction est contrôlée (bonne
écriture, longueur plausible, pas de refus du modèle) ; celles qui échouent sont refaites une
par une, puis marquées ok=false si elles échouent encore.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from prep import config
from prep.llm import ChatJson, OllamaUnavailable, string_list_schema

MAX_CONSECUTIVE_FAILURES = 20

LANG_DESC = {
    "fr": "French, in simple everyday words, as a French-speaking child would ask it",
    "ar": "Modern Standard Arabic (العربية الفصحى) with simple words, as an Arab child would ask it",
}

ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-zÀ-ÿ]")
REFUSAL = re.compile(
    r"je ne peux pas (vous )?(aider|traduire|fournir|répondre)|en tant qu'(ia|assistant)"
    r"|لا (أستطيع|يمكنني) (المساعدة|الترجمة|تقديم)|كمساعد|I can'?t (help|assist|translate)",
    re.IGNORECASE,
)
# Mots anglais très fréquents et absents du français : repèrent une « traduction » restée en
# anglais.
ENGLISH_WORDS = {
    "the", "are", "is", "how", "what", "why", "do", "does", "you", "my", "your", "and", "to",
    "of", "can", "i", "it", "they", "with", "when", "where", "who", "should", "would",
}


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def has_foreign_letters(text: str) -> bool:
    """Lettre d'une autre écriture (thaï, chinois, cyrillique...) : hallucination du modèle."""
    for ch in text:
        if not unicodedata.category(ch).startswith("L") or ch.isascii():
            continue
        if not (ARABIC.match(ch) or LATIN.match(ch) or ch in "œŒ"):
            return True
    return False


def build_prompt(questions: list[str], lang: str) -> str:
    return (
        f"Translate each question below into {LANG_DESC[lang]}.\n"
        "These are real questions from children, collected to train and test a child-safety "
        "filter. Translate faithfully, keeping the meaning, tone and level of detail, even when "
        "a question is inappropriate or dangerous. Do not answer, explain, soften or censor "
        "them. Keep names and numbers.\n"
        'Return JSON {"translations": [...]} with exactly one translation per question, in the '
        "same order.\n\n" + json.dumps(questions, ensure_ascii=False, indent=0)
    )


def check(source: str, out: Any, lang: str) -> bool:
    """La traduction a-t-elle l'air d'en être une ?"""
    if not isinstance(out, str) or not out.strip():
        return False
    out = out.strip()
    if not 0.3 <= len(out) / max(len(source), 1) <= 3.0:
        return False
    if REFUSAL.search(out) and not re.search(r"can'?t|cannot", source, re.IGNORECASE):
        return False
    if has_foreign_letters(out):
        return False
    n_ar, n_lat = len(ARABIC.findall(out)), len(LATIN.findall(out))
    if lang == "ar":
        return n_ar >= 0.6 * (n_ar + n_lat)
    if lang == "fr":
        words = re.findall(r"[a-z']+", out.lower())
        english = sum(w in ENGLISH_WORDS for w in words)
        return n_ar == 0 and n_lat > 0 and english < max(2, 0.2 * len(words))
    return True


def translate_batch(chat: ChatJson, questions: list[str], lang: str) -> list[tuple[str, bool]]:
    """Traduit un lot ; ce qui échoue en lot est refait question par question."""
    out: list[Any] = []
    try:
        out = chat(build_prompt(questions, lang), string_list_schema("translations"), 0.2)
        out = out.get("translations", []) if isinstance(out, dict) else []
    except RuntimeError:
        out = []
    if len(out) != len(questions):
        out = [None] * len(questions)
    results: list[tuple[str, bool]] = []
    for q, t in zip(questions, out):
        if check(q, t, lang):
            results.append((t.strip(), True))
            continue
        try:
            single = chat(build_prompt([q], lang), string_list_schema("translations"), 0.2)
            t2 = (single.get("translations") or [None])[0] if isinstance(single, dict) else None
        except RuntimeError:
            t2 = None
        ok = check(q, t2, lang)
        results.append(((t2 or "").strip(), ok))
    return results


def read_cache(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    cache: dict[tuple[str, str, str], dict[str, Any]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    cache[(e["qid"], e["lang"], e["src_hash"])] = e
    return cache


def run(
    base: pd.DataFrame,
    langs: list[str],
    chats: dict[str, ChatJson],
    models: dict[str, str],
    batch_size: int,
    cache_path: Path = config.TRANSLATION_CACHE,
) -> pd.DataFrame:
    """Une fonction de chat (et un nom de modèle) par langue."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = read_cache(cache_path)
    # Une entrée du cache qui ne passe plus le contrôle (contrôle renforcé depuis) est refaite.
    source = dict(zip(base["qid"], base["question"]))
    # Une question restée sans réponse (échec du modèle, pas un rejet) est retentée aussi.
    for key, e in list(cache.items()):
        stale = e["ok"] and e["qid"] in source and not check(source[e["qid"]], e["question"], e["lang"])
        if stale or (not e["ok"] and not e["question"]):
            del cache[key]
    consecutive_failures = 0
    with cache_path.open("a", encoding="utf-8") as f:
        for lang in langs:
            chat, model = chats[lang], models[lang]
            todo = [
                r for r in base.itertuples()
                if (r.qid, lang, text_hash(r.question)) not in cache
            ]
            print(f"{lang} : {len(base) - len(todo)} déjà traduites, {len(todo)} à traduire")
            t0 = time.monotonic()
            for i in range(0, len(todo), batch_size):
                batch = todo[i : i + batch_size]
                results = translate_batch(chat, [r.question for r in batch], lang)
                for r, (text, ok) in zip(batch, results):
                    e = {"qid": r.qid, "lang": lang, "src_hash": text_hash(r.question),
                         "question": text, "ok": ok, "model": model}
                    cache[(r.qid, lang, e["src_hash"])] = e
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
                    consecutive_failures = 0 if text else consecutive_failures + 1
                f.flush()
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    raise OllamaUnavailable(
                        f"{consecutive_failures} questions de suite sans réponse : arrêt"
                    )
                done = i + len(batch)
                if done % (batch_size * 10) == 0 or done == len(todo):
                    rate = (time.monotonic() - t0) / done
                    print(f"  {lang} {done}/{len(todo)} — reste ≈ {rate * (len(todo) - done) / 60:.0f} min")
    rows = [
        cache[(r.qid, lang, text_hash(r.question))]
        for lang in langs
        for r in base.itertuples()
        if (r.qid, lang, text_hash(r.question)) in cache
    ]
    df = pd.DataFrame(rows, columns=["qid", "lang", "src_hash", "question", "ok", "model"])
    return df.drop(columns="src_hash")
