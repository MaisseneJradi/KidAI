"""Signaux par mots-clés qui complètent Qwen3Guard pour la politique B2 (étape 5).

Mesuré à l'étape 5 : le gardien juge « safe » des sujets délicats (mort, guerre, sexualité…)
et un signal d'emprise (« un adulte m'a dit de garder un secret »). Ces listes courtes et
transparentes rattrapent ces cas. À faire relire par un locuteur natif (arabe, derja).

Les textes sont normalisés avant comparaison : minuscules, accents et signes diacritiques
arabes retirés, variantes de l'alif unifiées. Les motifs français et derja latins sont des
débuts de mots (« mour » couvre mourir, mourrai…).
"""

import re
import unicodedata
from dataclasses import dataclass

# --- Détresse ou danger : l'enfant (ou quelqu'un d'autre) a besoin d'un adulte -> ASK_ADULT.
_DISTRESS_LATIN = [
    r"je veux mourir",
    r"j ai envie de mourir",
    r"me suicid",
    r"me tuer\b",
    r"me faire du mal",
    r"me faire mal expres",
    r"j ai peur",
    r"on me frappe",
    r"me frapp",
    r"me tap(e|ent)\b",
    r"me harcel",
    r"harcelement",
    r"me touch",
    r"personne ne m aime",
    r"je suis tout le temps triste",
    r"je veux (le|la|les) (tuer|frapper)",
    r"je vais (le|la|les) tuer",
    # derja en lettres latines
    r"nheb nmout",
    r"n7eb nmout",
    r"khay(e|a)f",
    r"yodh?rob",
    r"ydh?arb",
    r"nheb nodh?rob",
    r"n7eb nodh?rob",
    r"sekina",
]
_DISTRESS_ARABIC = [
    "اريد ان اموت",
    "اقتل نفسي",
    "اوذي نفسي",
    "خايف",
    "خائف",
    "يضربني",
    "تضربني",
    "يضربونني",
    "يتحرش",
    "يلمسني",
    "لا احد يحبني",
    # derja en lettres arabes
    "نحب نموت",
    "يضربو فيا",
    "نحب نضرب",
]

# --- Secret à cacher aux parents (signal d'emprise) -> ASK_ADULT avec un texte pré-écrit :
#     mesuré à l'étape 5, le modèle 4B approuve parfois le secret (« c'est normal »).
_SECRET_LATIN = [
    r"garder (un|le|ce) secret",
    r"c est (un|notre) secret",
    r"(ne|rien) (rien )?dire a (maman|papa|mes parents|personne)",
    r"ne (le |la |les )?dis (pas|rien) a (maman|papa|tes parents|personne)",
    r"personne ne doit savoir",
    # derja en lettres latines
    r"ma t(9|q)oul(ech|ch)? ?l ?(mama|ommek|bebek|babak|ba?ba)",
]
_SECRET_ARABIC = [
    "احتفظ بسر",
    "سر ولا",
    "لا تخبر",
    "لا اخبر امي",
    "لا اخبر ابي",
    "لا تقل لامك",
    # derja en lettres arabes
    "ما تقولش",
]

# --- Sujets délicats mais légitimes -> REWRITE pour les plus jeunes.
_SENSITIVE_LATIN = [
    r"\bmort",
    r"\bmour",
    r"\bmeur",
    r"\bdeces",
    r"\bguerre",
    r"\bsex",
    r"\bbebes? vien",
    r"viennent les bebes",
    r"faire (des|un) bebe",
    r"\bdrogu",
    r"\balcool",
    r"\bcigarett",
    r"\bfum(e|er|ent)\b",
    r"\btabac",
    r"\bdivorc",
    r"\bcancer",
    r"\battentat",
    r"\bterroris",
    r"\bracis",
    r"\bviol\b",
    r"\bsang\b",
    # derja en lettres latines
    r"\bmout\b",
    r"\b7arb\b",
    r"\bdokhan",
]
_SENSITIVE_ARABIC = [
    "موت",
    "الموت",
    "يموت",
    "حرب",
    "الحرب",
    "جنس",
    "مخدرات",
    "سجائر",
    "تدخين",
    "خمر",
    "طلاق",
    "سرطان",
    "ارهاب",
    "عنصري",
]

# --- Tentatives de contournement des règles -> BLOCK.
_JAILBREAK_LATIN = [
    r"ignore (tes|les|toutes tes) (regles|instructions|consignes)",
    r"oublie tes (regles|consignes)",
    r"tu n es plus kotty",
    r"fais semblant (de ne pas|que tu n as pas)",
    r"mode developpeur",
    r"sans (filtre|regles)",
    r"ignore (your|all|previous) (rules|instructions)",
    r"\bjailbreak",
    r"dis (des|moi des) gros mots",
]
_JAILBREAK_ARABIC = ["تجاهل القواعد", "تجاهل تعليماتك", "انس القواعد"]

_ARABIC_DIACRITICS = re.compile(r"[ً-ْـ]")  # tachkil et tatwil


def normalize(text: str) -> str:
    text = text.lower().replace("’", "'").replace("'", " ")
    text = _ARABIC_DIACRITICS.sub("", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    # Accents latins retirés ; les lettres arabes ne se décomposent pas, elles restent intactes.
    decomposed = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def _compile(latin: list[str], arabic: list[str]) -> list[re.Pattern[str]]:
    patterns = [re.compile(p) for p in latin]
    patterns += [re.compile(re.escape(normalize(w))) for w in arabic]
    return patterns


_DISTRESS = _compile(_DISTRESS_LATIN, _DISTRESS_ARABIC)
_SECRET = _compile(_SECRET_LATIN, _SECRET_ARABIC)
_SENSITIVE = _compile(_SENSITIVE_LATIN, _SENSITIVE_ARABIC)
_JAILBREAK = _compile(_JAILBREAK_LATIN, _JAILBREAK_ARABIC)


@dataclass(frozen=True)
class Signals:
    distress: bool = False  # vrai aussi pour un secret (ci-dessous)
    secret: bool = False
    sensitive: bool = False
    jailbreak: bool = False


def detect(question: str) -> Signals:
    text = normalize(question)
    secret = any(p.search(text) for p in _SECRET)
    return Signals(
        distress=secret or any(p.search(text) for p in _DISTRESS),
        secret=secret,
        sensitive=any(p.search(text) for p in _SENSITIVE),
        jailbreak=any(p.search(text) for p in _JAILBREAK),
    )
