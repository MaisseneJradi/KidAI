"""Réponses sûres par défaut (F-S06) : textes fixes, relus à la main, jamais générés.

Utilisées seulement quand la réponse générée ne peut pas être montrée (refusée par le
gardien, ou Kotty indisponible pour ASK_ADULT / BLOCK) : « unsafe_input » pour BLOCK,
« distress » pour ASK_ADULT, « unsafe_output » pour ALLOW / REWRITE / REDIRECT.
« secret » est toujours utilisé, sans génération, quand l'enfant parle d'un secret à cacher
à ses parents (signal d'emprise).
"""

from typing import Literal

Reason = Literal["unsafe_input", "distress", "secret", "unsafe_output"]
Lang = Literal["fr", "ar"]

_REPLIES: dict[Reason, dict[Lang, str]] = {
    # La question elle-même a été jugée à risque : Kotty n'a pas été appelé.
    "unsafe_input": {
        "fr": (
            "Ça, je préfère ne pas en parler avec toi. Ce n'est pas grave d'avoir posé la "
            "question ! Et si on parlait d'autre chose ? Sais-tu pourquoi les étoiles brillent ?"
        ),
        "ar": (
            "أفضّل ألّا أتحدث عن هذا الموضوع. لا بأس أنك سألت! ما رأيك أن نتحدث عن شيء آخر؟ "
            "هل تعرف لماذا تلمع النجوم؟"
        ),
    },
    # L'enfant exprime une détresse : ne jamais changer de sujet, orienter vers un adulte.
    # (L'action ASK_ADULT et l'alerte parent arrivent à l'étape 5.)
    "distress": {
        "fr": (
            "Merci de me l'avoir dit, c'est courageux. Ce que tu ressens est important. "
            "Parles-en tout de suite à un parent ou à un adulte de confiance : ils sont là pour "
            "t'aider, et tu peux compter sur eux."
        ),
        "ar": (
            "شكرًا لأنك أخبرتني، هذا شجاع. ما تشعر به مهم. "
            "تحدّث الآن مع أحد والديك أو مع شخص كبير تثق به: هم هنا لمساعدتك، ويمكنك الاعتماد عليهم."
        ),
    },
    # Un secret à cacher aux parents (signal d'emprise) : toujours ce texte, jamais généré.
    "secret": {
        "fr": (
            "Merci de me l'avoir dit, tu as bien fait. Un adulte ne doit jamais te demander de "
            "cacher un secret à tes parents : ce n'est pas un bon secret. Tu as le droit d'en "
            "parler à maman, à papa ou à un adulte de confiance, et tu ne seras pas grondé."
        ),
        "ar": (
            "شكرًا لأنك أخبرتني، لقد أحسنت. لا يجب على أي شخص كبير أن يطلب منك إخفاء سر عن "
            "والديك: هذا ليس سرًّا جيدًا. من حقك أن تتحدث مع أمك أو أبيك أو شخص كبير تثق به، "
            "ولن يغضب منك أحد."
        ),
    },
    # La question était sûre mais la réponse générée n'a pas passé le contrôle.
    "unsafe_output": {
        "fr": (
            "Oups, je n'ai pas trouvé une bonne façon d'expliquer ça. Tu peux poser ta question "
            "autrement, ou me demander autre chose !"
        ),
        "ar": (
            "عذرًا، لم أجد طريقة جيدة لشرح ذلك. "
            "يمكنك أن تطرح سؤالك بطريقة أخرى، أو تسألني عن شيء آخر!"
        ),
    },
}


def safe_reply(reason: Reason, lang: Lang) -> str:
    return _REPLIES[reason][lang]
