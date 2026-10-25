import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import download_cnp as cnp  # noqa: E402

# Extrait réel d'une page de résultats (4e année, الإيقاظ العلمي, élève), plus une ligne
# fictive en deux parties pour couvrir le rowspan.
RESULTS_HTML = """
<table width="100%" border="0" dir="rtl">
<tr><tr><th height ="28">الرمز</th><th>العنوان</th><th>التحميل</th></tr></tr>
<tr class ="tr_content">
<td rowspan='1'>103404</td>
<td rowspan='1'>الإيقاظ العلمي</td>
<td><a href=../../../../arabic/PDF/103404P00.pdf target="_blank">Partie 1</a></td>
</tr>
<tr class ="tr_content">
<td rowspan='2'>101401</td>
<td rowspan='2'>Mon livre de français</td>
<td><a href=../../../../arabic/PDF/101401P01.pdf target="_blank">Partie 1</a></td>
</tr>
<tr class ="tr_content">
<td><a href=../../../../arabic/PDF/101401P02.pdf target="_blank">Partie 2</a></td>
</tr>
</table>
"""


def test_parse_results_resolves_urls_and_rowspan() -> None:
    assert cnp.parse_results(RESULTS_HTML) == [
        ("103404", "الإيقاظ العلمي", "Partie 1", "https://cnp.com.tn/arabic/PDF/103404P00.pdf"),
        ("101401", "Mon livre de français", "Partie 1", "https://cnp.com.tn/arabic/PDF/101401P01.pdf"),
        ("101401", "Mon livre de français", "Partie 2", "https://cnp.com.tn/arabic/PDF/101401P02.pdf"),
    ]


def test_parse_results_empty_page() -> None:
    assert cnp.parse_results("<html><table></table></html>") == []


def test_safe_name_removes_forbidden_characters() -> None:
    assert cnp.safe_name('Maths: 1/2 "test"?') == "Maths_ 1_2 _test__"
    assert cnp.safe_name("   ") == "sans_titre"


def test_detect_lang() -> None:
    assert cnp.detect_lang("الرياضيات", "fr") == "ar"
    assert cnp.detect_lang("Mon livre de français", "fr") == "fr"


def test_is_valid_checks_size_and_hash(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cnp, "OUT_DIR", tmp_path)
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 contenu")
    entry = {"status": "ok", "fichier": "a.pdf", "taille": pdf.stat().st_size, "sha256": cnp.sha256(pdf)}
    assert cnp.is_valid(entry)

    pdf.write_bytes(b"%PDF-1.4 abime!!")  # même taille, contenu différent
    assert not cnp.is_valid(entry)
    assert not cnp.is_valid({**entry, "status": "failed"})
    assert not cnp.is_valid(None)
