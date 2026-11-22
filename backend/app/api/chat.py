import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentParent, DbSession, owned_child
from app.core.lang import Lang, reply_lang
from app.db.models import Alert, Child, Message
from app.schemas import Action, MessageIn, MessageOut, OutputCheck, Safety
from app.services.llm import LLMReply, LLMUnavailableError, OllamaLLM, get_llm
from app.services.policy import Policy, State, get_policy
from app.services.safe_replies import Reason, safe_reply
from app.services.safety import GuardVerdict, QwenGuard, SafetyUnavailableError, get_guard
from app.services.signals import detect

router = APIRouter(prefix="/api/chat", tags=["chat"])

LLM = Annotated[OllamaLLM, Depends(get_llm)]
Guard = Annotated[QwenGuard, Depends(get_guard)]
PolicyDep = Annotated[Policy, Depends(get_policy)]

UNAVAILABLE = "Kotty se repose un instant, réessaie dans un moment."

# Texte pré-écrit utilisé quand la réponse générée ne peut pas être montrée.
_FALLBACK: dict[Action, Reason] = {
    "ALLOW": "unsafe_output",
    "REWRITE": "unsafe_output",
    "REDIRECT": "unsafe_output",
    "ASK_ADULT": "distress",
    "BLOCK": "unsafe_input",
}


@dataclass
class Outcome:
    text: str
    action: Action
    output_check: OutputCheck
    reply: LLMReply | None = None
    output_ms: int = 0


def _generate(
    llm: OllamaLLM, guard: QwenGuard, child: Child, question: str, lang: Lang, action: Action
) -> Outcome:
    """Kotty écrit la réponse de l'action choisie ; le gardien la contrôle avant affichage.

    ALLOW / REWRITE / REDIRECT : si Kotty ou le gardien est indisponible, l'erreur remonte (503).
    ASK_ADULT / BLOCK : jamais d'erreur pour l'enfant, on se replie sur le texte pré-écrit.
    """
    critical = action in ("ASK_ADULT", "BLOCK")
    try:
        reply = llm.answer(question, age=child.age, grade=child.grade, lang=lang, action=action)
        verdict_out = guard.check_output(question, reply.text)
    except (LLMUnavailableError, SafetyUnavailableError):
        if not critical:
            raise
        return Outcome(safe_reply(_FALLBACK[action], lang), action, "skipped")

    if verdict_out.is_safe:
        return Outcome(reply.text, action, "pass", reply, verdict_out.latency_ms)
    # Réponse refusée par le gardien : jamais montrée ni enregistrée.
    fallback_action: Action = action if critical else "BLOCK"
    text = safe_reply(_FALLBACK[action], lang)
    return Outcome(text, fallback_action, "fail", reply, verdict_out.latency_ms)


@router.post("/{child_id}/messages")
def send_message(
    child_id: str,
    payload: MessageIn,
    parent: CurrentParent,
    db: DbSession,
    llm: LLM,
    guard: Guard,
    policy: PolicyDep,
) -> MessageOut:
    """Question → contrôle d'entrée → choix de l'action (B2) → Kotty → contrôle de sortie.

    Étape 5 : les 5 actions de l'Annexe C, et une alerte au parent pour chaque ASK_ADULT.
    """
    child = owned_child(db, parent, child_id)
    question = payload.question
    # Question en lettres arabes → réponse en arabe, quelle que soit la langue de l'appareil.
    lang = reply_lang(question, payload.lang)
    signals = detect(question)
    start = time.perf_counter()

    try:
        verdict_in = guard.check_input(question)
    except SafetyUnavailableError as exc:
        if not signals.distress:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE) from exc
        # Gardien en panne mais détresse évidente : on oriente vers un adulte quand même.
        verdict_in = GuardVerdict("unsafe", (), 0)

    state = State(
        age=child.age,
        risk=verdict_in.level,
        categories=verdict_in.categories,
        signals=signals,
        caution="renforce" if child.caution_level == "renforce" else "standard",
    )
    action = policy.decide(state)
    try:
        if action == "ASK_ADULT" and signals.secret:
            # Signal d'emprise : texte pré-écrit, chaque mot est contrôlé (pas de génération).
            outcome = Outcome(safe_reply("secret", lang), action, "skipped")
        else:
            outcome = _generate(llm, guard, child, question, lang, action)
    except (LLMUnavailableError, SafetyUnavailableError) as exc:
        # Rien n'est enregistré ni montré : jamais de réponse non vérifiée.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE) from exc

    message = Message(
        child_id=child.id,
        question=question,
        answer=outcome.text,
        action=outcome.action,
        lang=lang,
        input_risk=verdict_in.level,
        input_category=verdict_in.category,
        output_check=outcome.output_check,
        rag_ref=None,
        latency_ms=round((time.perf_counter() - start) * 1000),
        safety_latency_ms=verdict_in.latency_ms + outcome.output_ms,
        model_name=outcome.reply.model_name if outcome.reply else None,
        prompt_version=outcome.reply.prompt_version if outcome.reply else None,
        policy_version=policy.version,
    )
    db.add(message)
    if outcome.action == "ASK_ADULT":
        # F-P03 : le parent est prévenu, même si la réponse est le texte de repli.
        db.add(Alert(child_id=child.id, message=message, type="ASK_ADULT"))
    db.commit()

    return MessageOut(
        message_id=message.id,
        text=outcome.text,
        action=outcome.action,
        lang=lang,
        rag_source=None,
        image_status="none",
        safety=Safety(input_risk=verdict_in.level, output_check=outcome.output_check),
    )
