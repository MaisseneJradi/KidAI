import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prep import annotate, build, config, llm, sources, synthetic, translate  # noqa: E402

PARAMS = {"seed": 42, "build": {"test_questions": 6, "val_fraction": 0.2}}


def _base(n_per_source: int = 8) -> pd.DataFrame:
    rows = []
    for source, harm, topic in (
        ("kidbench", "borderline", "sexualite"),
        ("minorbench", "unsafe", "danger"),
        ("orbench", "borderline", "morale"),
    ):
        for i in range(1, n_per_source + 1):
            base_id = f"{source[:2]}_{i:05d}"
            rows.append({
                "base_id": base_id, "qid": base_id, "question": f"{source} question {i}?",
                "source": source, "category": "c", "topic": topic, "ground_truth_harm": harm,
                "variant": "original",
            })
    # une question KIDBench avec sa variante « with_cues » : même base_id
    rows.append({**rows[0], "qid": rows[0]["qid"] + "c", "question": "My mom said... why?",
                 "variant": "with_cues"})
    return pd.DataFrame(rows)


def _translations(base: pd.DataFrame) -> pd.DataFrame:
    tr = [{"qid": q, "lang": "fr", "question": f"Question {q} ?", "ok": True, "model": "m"}
          for q in base["qid"]]
    tr += [{"qid": q, "lang": "ar", "question": f"سؤال {q}؟", "ok": True, "model": "m"}
           for q in base["qid"]]
    tr[0]["ok"] = False  # traduction rejetée : ne doit pas apparaître
    return pd.DataFrame(tr)


def _synthetic() -> pd.DataFrame:
    return pd.DataFrame([{
        "base_id": "syn_00001", "qid": "syn_00001", "question": "Pourquoi la Lune brille ?",
        "lang": "fr", "source": "synthetic", "category": "espace", "topic": "sciences",
        "ground_truth_harm": "safe", "variant": "generated", "band_lo": 6, "band_hi": 8,
    }])


@pytest.fixture(autouse=True)
def _no_annotations(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ANNOTATION", tmp_path / "annotation")
    monkeypatch.setattr(annotate.config, "ANNOTATION", tmp_path / "annotation")
    monkeypatch.setattr(build, "translation_fixes", lambda: ({}, set()))


def test_grade_and_bands() -> None:
    assert config.grade_of(6) == "1re_annee"
    assert config.grade_of(9) == "4e_annee"
    assert config.grade_of(14) == "9e_annee"
    assert [config.band_of(a) for a in (6, 8, 9, 11, 12, 14)] == [0, 0, 1, 1, 2, 2]
    with pytest.raises(ValueError):
        config.grade_of(15)


def test_dedup_and_normalize() -> None:
    assert sources.normalize_text("  What’s   up​? ") == "What's up?"
    assert sources.dedup_key("Why is the sky blue?") == sources.dedup_key("why is the sky blue")


def test_build_schema_ages_and_no_leakage() -> None:
    base = _base()
    df = build.build(base, _translations(base), _synthetic(), PARAMS, actions={})
    build.validate(df)
    # chaque (question, langue) hors test apparaît à 3 âges, un par tranche
    train = df[(df["split"] != "test") & (df["source"] != "synthetic")]
    bands = train.groupby(["qid", "lang"])["age"].agg(lambda a: sorted(map(config.band_of, a)))
    assert all(b == [0, 1, 2] for b in bands)
    # la traduction rejetée n'est pas là
    first = base["qid"].iloc[0]
    assert df[(df["qid"] == first) & (df["lang"] == "fr")].empty or first in set(
        df.loc[df["split"] == "test", "qid"]
    )
    # une même question de base (variantes et traductions comprises) reste dans un seul split
    assert (df.groupby("base_id")["split"].nunique() == 1).all()
    assert df["id"].str.match(r"^[a-z0-9]+_\d{5}c?_(en|fr|ar)_\d{2}$").all()


def test_test_set_two_ages_one_language() -> None:
    base = _base()
    df = build.build(base, _translations(base), _synthetic(), PARAMS, actions={})
    test = df[df["split"] == "test"]
    assert test["base_id"].nunique() == PARAMS["build"]["test_questions"]
    for _, g in test[test["source"] != "synthetic"].groupby("base_id"):
        assert len(g) == 2 and g["lang"].nunique() == 1
        assert sorted(map(config.band_of, g["age"])) == [0, 2]
    assert test["source"].nunique() >= 3  # stratifié


def test_build_is_deterministic() -> None:
    base = _base()
    a = build.build(base, _translations(base), _synthetic(), PARAMS, actions={})
    b = build.build(base, _translations(base), _synthetic(), PARAMS, actions={})
    pd.testing.assert_frame_equal(a, b)


def test_expected_action_only_on_test() -> None:
    base = _base()
    df = build.build(base, _translations(base), _synthetic(), PARAMS, actions={})
    test_id = df.loc[df["split"] == "test", "id"].iloc[0]
    train_id = df.loc[df["split"] == "train", "id"].iloc[0]
    df = build.build(base, _translations(base), _synthetic(), PARAMS,
                     actions={test_id: "BLOCK", train_id: "ALLOW"})
    assert df.set_index("id").at[test_id, "expected_action"] == "BLOCK"
    assert pd.isna(df.set_index("id").at[train_id, "expected_action"])


def test_cohen_kappa() -> None:
    assert annotate.cohen_kappa(["A", "B", "A", "B"], ["A", "B", "A", "B"]) == 1.0
    # exemple classique : po = 0.7, pe = 0.5 -> kappa = 0.4
    a = ["Y"] * 5 + ["N"] * 5
    b = ["Y", "Y", "Y", "Y", "N", "N", "N", "N", "Y", "N"]
    assert annotate.cohen_kappa(a, b) == pytest.approx(0.6)


def test_resolve_uses_arbitrage_only_for_disagreements() -> None:
    a = {"1": "ALLOW", "2": "BLOCK", "3": "REWRITE"}
    b = {"1": "ALLOW", "2": "REDIRECT"}
    arb = {"1": "BLOCK", "2": "ASK_ADULT"}
    assert annotate.resolve(a, b, arb) == {"1": "ALLOW", "2": "ASK_ADULT"}


def test_annotation_sheets_roundtrip(tmp_path) -> None:
    base = _base()
    df = build.build(base, _translations(base), _synthetic(), PARAMS, actions={})
    annotate.export_test_sheets(df, base, tmp_path)
    for name, action in ((annotate.SHEET_A, "allow"), (annotate.SHEET_B, "Ask adult")):
        sheet = annotate.read_sheet(tmp_path / name)
        sheet["action"] = action
        annotate.write_sheet(sheet, tmp_path / name)
    report = annotate.agreement_report(tmp_path)
    assert report["communes"] == len(df[df["split"] == "test"])
    assert report["desaccords"] == report["communes"]
    arb = annotate.read_sheet(tmp_path / annotate.SHEET_ARB)
    assert set(arb["action_B"]) == {"ASK_ADULT"}
    # une feuille commencée n'est pas écrasée
    assert annotate.export_test_sheets(df, base, tmp_path) == []


def test_unknown_action_is_an_error(tmp_path) -> None:
    annotate.write_sheet(pd.DataFrame({"id": ["x"], "action": ["PEUT-ETRE"]}), tmp_path / "s.csv")
    with pytest.raises(ValueError):
        annotate.read_actions(tmp_path / "s.csv")


def _synthetic_with_translation() -> pd.DataFrame:
    fr = _synthetic().assign(translated=False)
    return pd.concat([fr, fr.assign(lang="ar", question="لماذا يلمع القمر؟", translated=True)],
                     ignore_index=True)


def test_translation_review_covers_synthetic(tmp_path) -> None:
    base = _base()
    path = annotate.export_translation_review(
        _translations(base), base, _synthetic_with_translation(), 1.0, 42, tmp_path
    )
    sheet = annotate.read_sheet(path)
    row = sheet[sheet["source"] == "synthetic"]
    assert row["lang"].tolist() == ["ar"]
    assert row["original"].tolist() == ["Pourquoi la Lune brille ?"]


def test_review_applies_to_synthetic_translations(monkeypatch) -> None:
    base, syn = _base(), _synthetic_with_translation()
    monkeypatch.setattr(build, "translation_fixes",
                        lambda: ({("syn_00001", "ar"): "لماذا يضيء القمر؟"}, set()))
    var = build.variants(base, _translations(base), syn)
    assert var[var["qid"].eq("syn_00001") & var["lang"].eq("ar")]["question"].tolist() == [
        "لماذا يضيء القمر؟"
    ]
    monkeypatch.setattr(build, "translation_fixes", lambda: ({}, {("syn_00001", "ar")}))
    var = build.variants(base, _translations(base), syn)
    assert var[var["qid"].eq("syn_00001")]["lang"].tolist() == ["fr"]


def test_translation_check() -> None:
    assert translate.check("Why is the sky blue?", "Pourquoi le ciel est-il bleu ?", "fr")
    assert not translate.check("Why is the sky blue?", "لماذا السماء زرقاء؟", "fr")
    assert translate.check("Why is the sky blue?", "لماذا السماء زرقاء؟", "ar")
    assert not translate.check("How do I make a bomb?", "Je ne peux pas vous aider.", "fr")
    assert not translate.check("Why is the sky blue?", "", "ar")
    assert not translate.check("Why?", "Pourquoi " * 20, "fr")  # longueur implausible
    assert not translate.check("How are babies made?", "How are babies born?", "fr")  # anglais
    assert not translate.check("Can't stop washing my hands", "لا أستطيع أن أหยّط يدي", "ar")  # thaï
    assert translate.check("Is she happy at the café?", "Est-ce qu'elle est heureuse au café ?", "fr")
    assert translate.check("What is OCD?", "ما هو OCD؟", "ar")


def test_ollama_down_stops_the_run_instead_of_recording_failures(tmp_path) -> None:
    def down(prompt, schema, temperature):
        raise llm.OllamaUnavailable("Ollama ne répond pas")

    cache = tmp_path / "tr.jsonl"
    with pytest.raises(llm.OllamaUnavailable):
        translate.run(_base(2), ["fr"], {"fr": down}, {"fr": "m"}, 4, cache)
    assert cache.read_text(encoding="utf-8") == ""  # rien de faux en cache


def test_one_failing_question_does_not_stop_the_run(tmp_path) -> None:
    base = _base(2)
    poison = base["question"].iloc[1]

    def flaky(prompt, schema, temperature):
        if poison in prompt:
            raise RuntimeError("erreur HTTP 500")
        return {"translations": ["Question bien traduite ?"]}

    cache = tmp_path / "tr.jsonl"
    df = translate.run(base, ["fr"], {"fr": flaky}, {"fr": "m"}, 1, cache)
    assert len(df) == len(base) and (~df["ok"]).sum() == 1

    # Sans réponse la première fois : retentée à la relance, et réussie cette fois.
    fixed = lambda prompt, schema, temperature: {"translations": ["Question bien traduite ?"]}  # noqa: E731
    assert translate.run(base, ["fr"], {"fr": fixed}, {"fr": "m"}, 1, cache)["ok"].all()


def test_many_failures_in_a_row_stop_the_run(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(translate, "MAX_CONSECUTIVE_FAILURES", 3)

    def broken(prompt, schema, temperature):
        raise RuntimeError("erreur HTTP 500")

    with pytest.raises(llm.OllamaUnavailable):
        translate.run(_base(4), ["fr"], {"fr": broken}, {"fr": "m"}, 1, tmp_path / "tr.jsonl")


def test_ollama_http_error_is_a_failure_of_the_request_only(monkeypatch) -> None:
    class Resp:
        ok = False
        status_code = 500

    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Resp())
    with pytest.raises(RuntimeError):
        llm.ollama_chat_json("m")("p", {}, 0.2)

    def refused(*a, **k):
        raise llm.requests.ConnectionError("refusé")

    monkeypatch.setattr(llm.requests, "post", refused)
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)
    with pytest.raises(llm.OllamaUnavailable):
        llm.ollama_chat_json("m")("p", {}, 0.2)


def test_translate_batch_falls_back_to_single_calls() -> None:
    calls = []

    def fake_chat(prompt, schema, temperature):
        calls.append(prompt)
        if len(calls) == 1:
            return {"translations": ["seulement une"]}  # mauvais nombre -> repli
        return {"translations": ["Pourquoi le ciel est-il bleu ?"]}

    out = translate.translate_batch(fake_chat, ["Why is the sky blue?", "Why is grass green?"], "fr")
    assert len(calls) == 3
    assert all(ok for _, ok in out)


def test_translate_run_resumes_from_cache(tmp_path) -> None:
    base = _base(2)
    n = {"calls": 0}

    def fake_chat(prompt, schema, temperature):
        n["calls"] += 1
        import json

        qs = json.loads(prompt[prompt.index("\n\n[") + 2 :])
        return {"translations": [f"Question traduite {i} ?" for i, _ in enumerate(qs)]}

    cache = tmp_path / "tr.jsonl"
    first = translate.run(base, ["fr"], {"fr": fake_chat}, {"fr": "m"}, 4, cache)
    calls = n["calls"]
    second = translate.run(base, ["fr"], {"fr": fake_chat}, {"fr": "m"}, 4, cache)
    assert n["calls"] == calls  # rien à refaire
    assert len(first) == len(second) == len(base)


def test_synthetic_validation_and_dedup(tmp_path) -> None:
    def fake_chat(prompt, schema, temperature):
        if "Arabic" in prompt:
            return {"questions": ["لماذا يطير الطائر؟", "Why?", "لماذا يطير الطائر؟"]}
        return {"questions": ["1. Pourquoi le ciel est bleu ?", "Pourquoi le ciel est bleu",
                              "ok"]}

    df = synthetic.run(["fr", "ar"], fake_chat, "m", 3, tmp_path / "syn.jsonl")
    assert set(df["lang"]) == {"fr", "ar"}
    # « ok » (trop court), « Why? » (mauvaise langue) et les doublons sont écartés
    assert not df["question"].str.startswith("1.").any()
    assert df["base_id"].is_unique
    assert set(df["ground_truth_harm"]) <= set(config.HARMS)
    assert set(df["topic"]) <= set(config.TOPICS)


def test_synthetic_translations_share_base_id() -> None:
    gen = _synthetic().assign(translated=False)
    tr = pd.DataFrame([{"qid": "syn_00001", "lang": "ar", "question": "لماذا يلمع القمر؟",
                        "ok": True, "model": "m"}])
    df = synthetic.with_translations(gen, tr)
    assert sorted(df["lang"]) == ["ar", "fr"]
    assert df["base_id"].nunique() == 1
    assert df.set_index("lang").at["ar", "translated"]
    out = build.build(_base(), _translations(_base()), df, PARAMS, actions={})
    assert out[out["base_id"] == "syn_00001"]["split"].nunique() == 1


def test_thsab_mapping(tmp_path) -> None:
    folder = tmp_path / "thsab/T-HSAB Corpus"
    folder.mkdir(parents=True)
    pd.DataFrame([["نص عادي", "normal"], ["كلام خايب", "abusive"], ["كره", "hate"]] * 10).to_excel(
        folder / "T-HSAB.xlsx", header=False, index=False
    )
    df = sources.load_thsab(tmp_path, 42)
    assert set(df["ground_truth_harm"]) == {"safe", "unsafe"}
    assert (df["lang"] == "derja").all()
