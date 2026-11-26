"""Choix de l'action parmi 5 (F-S02). Interface commune aux politiques (règles, puis RL).

Étape 5 : RulesPolicy (baseline B2 du cahier, section 11.6), règles manuelles sur l'âge,
le verdict de Qwen3Guard, les signaux par mots-clés et le niveau de prudence du parent.
L'étape 7 ajoutera des politiques apprises avec la même interface ; B2 reste le repli.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.age import age_band
from app.services.llm import Action
from app.services.safety import RiskLevel
from app.services.signals import Signals

CautionLevel = Literal["standard", "renforce"]

SELF_HARM = "Suicide & Self-Harm"
VIOLENT = "Violent"
SEXUAL = "Sexual Content or Sexual Acts"
JAILBREAK = "Jailbreak"
POLITICAL = "Politically Sensitive Topics"


@dataclass(frozen=True)
class State:
    """Ce que la politique sait d'une question (l'état s de la section 11.2, version règles)."""

    age: int
    risk: RiskLevel
    categories: tuple[str, ...]
    signals: Signals
    caution: CautionLevel = "standard"


class Policy(Protocol):
    version: str

    def decide(self, state: State) -> Action: ...


class RulesPolicy:
    """Baseline B2 : la première règle qui s'applique décide (ordre = priorité)."""

    version = "b2-rules-v1"

    def decide(self, state: State) -> Action:
        cats = set(state.categories)
        strict = state.caution == "renforce"
        risky = state.risk != "safe"

        # 1. Détresse ou danger pour l'enfant (ou un autre) : un adulte, toujours.
        if state.signals.distress or SELF_HARM in cats:
            return "ASK_ADULT"
        # 2. Violence « controversée » : le plus souvent une victime (« on me frappe »).
        if VIOLENT in cats and state.risk == "controversial":
            return "ASK_ADULT"
        # 3. Tentative de contournement des règles.
        if state.signals.jailbreak or JAILBREAK in cats:
            return "BLOCK"
        # 4. Violence ou sexualité clairement dangereuses : pas de reformulation utile.
        if state.risk == "unsafe" and cats & {VIOLENT, SEXUAL}:
            return "BLOCK"
        # 5. Politique « controversée » : une réponse douce et neutre plutôt qu'un refus.
        if state.risk == "controversial" and POLITICAL in cats and not strict:
            return "REWRITE"
        # 6. Autre risque (illégal, contraire à l'éthique, données personnelles…) : sujet voisin.
        #    Mode strict : jamais ALLOW pour une question à risque.
        if risky:
            return "BLOCK" if strict and state.risk == "unsafe" else "REDIRECT"
        # 7. Sujet délicat mais légitime : en douceur pour les 6–11 ans (ou prudence renforcée).
        if state.signals.sensitive and (age_band(state.age) != "teen" or strict):
            return "REWRITE"
        # 8. Question normale.
        return "ALLOW"


def get_policy() -> Policy:
    return RulesPolicy()
