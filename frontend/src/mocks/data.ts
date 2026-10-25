// Données et logique simulées (étape 1). Profils fictifs, aucune donnée d'enfant réel.
// Le vrai backend (étapes 2 à 5) remplacera cette logique par Qwen3Guard + la politique RL.
import type { Action, Child, Lang, RagSource, Topic } from "../api/types";

export const MOCK_PIN = "1234";
export const MOCK_TOKEN = "mock-token";
export const IMAGE_DELAY_MS = 3000;

export type StoredChild = Omit<Child, "age">;

// Nés un 1er janvier : âge stable (7, 10, 13 ans) quelle que soit la date du jour.
const bornYearsAgo = (years: number) => `${new Date().getFullYear() - years}-01-01`;

export const initialChildren: StoredChild[] = [
  {
    id: "child_yasmine",
    first_name: "Yasmine",
    avatar: "🦊",
    birth_date: bornYearsAgo(7),
    sex: "fille",
    grade: "2e_annee",
    lang: "fr",
    caution_level: "standard",
    interests: ["animaux"],
    needs: [],
  },
  {
    id: "child_adam",
    first_name: "Adam",
    avatar: "🐢",
    birth_date: bornYearsAgo(10),
    sex: "garcon",
    grade: "5e_annee",
    lang: "ar",
    caution_level: "standard",
    interests: ["espace", "sport"],
    needs: [],
  },
  {
    id: "child_lina",
    first_name: "Lina",
    avatar: "🐼",
    birth_date: bornYearsAgo(13),
    sex: "fille",
    grade: "8e_annee",
    lang: "fr",
    caution_level: "renforce",
    interests: ["sciences", "art"],
    needs: [],
  },
];

interface Rule {
  action: Action;
  topic: Topic;
  key: string;
  words: string[];
}

// Ordre important : les règles les plus prudentes passent en premier.
const RULES: Rule[] = [
  {
    action: "BLOCK",
    topic: "autre",
    key: "block",
    words: ["arme", "drogue", "bombe", "سلاح", "مخدرات", "قنبلة", "sle7", "zatla"],
  },
  {
    action: "ASK_ADULT",
    topic: "autre",
    key: "ask_adult",
    words: [
      "peur",
      "triste",
      "frappe",
      "harcèle",
      "harcele",
      "حزين",
      "خائف",
      "يضربني",
      "khayef",
      "na5af",
    ],
  },
  {
    action: "REDIRECT",
    topic: "sciences",
    key: "redirect",
    words: ["pirater", "hacker", "mot de passe", "اختراق", "قرصنة", "hack"],
  },
  {
    action: "REWRITE",
    topic: "histoire",
    key: "rewrite",
    words: ["guerre", "mort", "meurt", "حرب", "موت", "يموت"],
  },
  {
    action: "ALLOW",
    topic: "sciences",
    key: "volcano",
    words: ["volcan", "بركان", "براكين", "bourkan"],
  },
  {
    action: "ALLOW",
    topic: "espace",
    key: "space",
    words: [
      "étoile",
      "etoile",
      "planète",
      "planete",
      "lune",
      "espace",
      "نجم",
      "كوكب",
      "القمر",
      "فضاء",
    ],
  },
  {
    action: "ALLOW",
    topic: "sciences",
    key: "sky",
    words: ["ciel", "سماء", "السماء"],
  },
  {
    action: "ALLOW",
    topic: "animaux",
    key: "animals",
    words: ["animal", "animaux", "chat", "chien", "lion", "oiseau", "حيوان", "قط", "أسد", "طائر"],
  },
  {
    action: "ALLOW",
    topic: "corps",
    key: "body",
    words: ["coeur", "cœur", "corps", "dent", "قلب", "جسم", "أسنان"],
  },
];

const DEFAULT_RULE: Rule = { action: "ALLOW", topic: "autre", key: "generic", words: [] };

export function classify(question: string): Rule {
  const q = question.toLowerCase();
  return RULES.find((r) => r.words.some((w) => q.includes(w))) ?? DEFAULT_RULE;
}

type Texts = Record<Lang, { short: string; more: string }>;

const ANSWERS: Record<string, Texts> = {
  volcano: {
    fr: {
      short:
        "Un volcan, c'est comme une montagne qui a très chaud à l'intérieur ! Sous la terre, il y a de la roche fondue, le magma. Quand la pression devient trop forte, il sort par le haut.",
      more: "C'est un peu comme une bouteille de soda qu'on secoue : le gaz pousse et tout jaillit. Sais-tu comment s'appelle le magma une fois dehors ?",
    },
    ar: {
      short:
        "البركان مثل جبل ساخن جدًا من الداخل! تحت الأرض توجد صخور ذائبة اسمها الصهارة. عندما يصبح الضغط قويًا جدًا تخرج من القمة.",
      more: "يشبه ذلك قارورة مشروب غازي نرجّها: الغاز يدفع فيخرج كل شيء. هل تعرف ماذا نسمّي الصهارة عندما تخرج؟",
    },
  },
  space: {
    fr: {
      short:
        "Les étoiles sont d'immenses boules de gaz très chaudes, comme notre Soleil, mais tellement loin qu'elles paraissent toutes petites.",
      more: "La lumière de certaines étoiles voyage pendant des milliers d'années avant d'arriver à tes yeux ! Quelle est l'étoile la plus proche de nous ?",
    },
    ar: {
      short: "النجوم كرات ضخمة من الغاز الساخن جدًا مثل شمسنا، لكنها بعيدة جدًا فتبدو صغيرة.",
      more: "ضوء بعض النجوم يسافر آلاف السنين قبل أن يصل إلى عينيك! ما هو أقرب نجم إلينا؟",
    },
  },
  sky: {
    fr: {
      short:
        "La lumière du Soleil contient toutes les couleurs. En traversant l'air, le bleu rebondit partout dans le ciel : c'est pour ça qu'on le voit bleu !",
      more: "Le soir, la lumière traverse plus d'air et c'est le rouge et l'orange qui arrivent jusqu'à nous. As-tu déjà vu un coucher de soleil tout orange ?",
    },
    ar: {
      short:
        "ضوء الشمس فيه كل الألوان. عندما يمر عبر الهواء يتبعثر اللون الأزرق في كل مكان، لذلك نرى السماء زرقاء!",
      more: "في المساء يقطع الضوء مسافة أطول في الهواء فيصلنا الأحمر والبرتقالي. هل رأيت غروبًا برتقاليًا؟",
    },
  },
  animals: {
    fr: {
      short:
        "Chaque animal est adapté à l'endroit où il vit : la fourrure tient chaud, les ailes servent à voler et les nageoires à nager.",
      more: "Les scientifiques appellent ça l'adaptation. Quel est ton animal préféré, et où vit-il ?",
    },
    ar: {
      short:
        "كل حيوان متكيّف مع المكان الذي يعيش فيه: الفرو يدفئه، والأجنحة للطيران، والزعانف للسباحة.",
      more: "يسمّي العلماء هذا التكيّف. ما هو حيوانك المفضل وأين يعيش؟",
    },
  },
  body: {
    fr: {
      short:
        "Ton cœur est un muscle qui fonctionne comme une pompe : il envoie le sang partout dans ton corps, jour et nuit.",
      more: "Il bat environ 100 000 fois par jour ! Sais-tu comment sentir ton cœur battre ?",
    },
    ar: {
      short: "قلبك عضلة تعمل مثل المضخة: يرسل الدم إلى كل جسمك ليلًا ونهارًا.",
      more: "ينبض حوالي مئة ألف مرة في اليوم! هل تعرف كيف تشعر بنبضات قلبك؟",
    },
  },
  generic: {
    fr: {
      short: "Super question ! Je vais t'expliquer simplement, avec un exemple de tous les jours.",
      more: "Plus tu poses de questions, plus tu découvres de choses. Qu'aimerais-tu savoir d'autre ?",
    },
    ar: {
      short: "سؤال رائع! سأشرح لك ببساطة مع مثال من الحياة اليومية.",
      more: "كلما طرحت أسئلة أكثر اكتشفت أشياء أكثر. ماذا تحب أن تعرف أيضًا؟",
    },
  },
  rewrite: {
    fr: {
      short:
        "C'est une question importante. Parfois, des pays ne sont pas d'accord et cela peut rendre des gens tristes. Aujourd'hui, beaucoup de personnes travaillent pour la paix.",
      more: "Si ce sujet te rend inquiet, tu peux en parler avec un adulte de confiance. Sais-tu ce qu'est un traité de paix ?",
    },
    ar: {
      short:
        "هذا سؤال مهم. أحيانًا لا تتفق بعض الدول وقد يجعل ذلك الناس حزينين. اليوم يعمل كثير من الناس من أجل السلام.",
      more: "إذا كان هذا الموضوع يقلقك يمكنك أن تتحدث مع شخص كبير تثق به. هل تعرف ما هي معاهدة السلام؟",
    },
  },
  redirect: {
    fr: {
      short:
        "Je ne peux pas t'aider à entrer dans le compte de quelqu'un d'autre. Mais je peux t'expliquer comment un bon mot de passe protège tes secrets !",
      more: "Un mot de passe solide mélange des lettres, des chiffres et des symboles. Veux-tu inventer une phrase secrète rigolote ?",
    },
    ar: {
      short:
        "لا أستطيع مساعدتك على الدخول إلى حساب شخص آخر. لكن يمكنني أن أشرح لك كيف تحمي كلمة السر القوية أسرارك!",
      more: "كلمة السر القوية تخلط الحروف والأرقام والرموز. هل تريد أن تخترع جملة سرية مضحكة؟",
    },
  },
  ask_adult: {
    fr: {
      short:
        "Je comprends que tu ressentes ça, et c'est bien d'en parler. Le mieux, c'est d'en parler tout de suite à un parent ou à un adulte de confiance : ils sont là pour t'aider.",
      more: "",
    },
    ar: {
      short:
        "أفهم ما تشعر به، ومن الجيد أن تتحدث عنه. الأفضل أن تتحدث الآن مع أحد والديك أو مع شخص كبير تثق به: هم هنا لمساعدتك.",
      more: "",
    },
  },
  block: {
    fr: {
      short:
        "Ça, je ne peux pas en parler. Et si on découvrait plutôt pourquoi les volcans explosent ?",
      more: "",
    },
    ar: {
      short: "لا أستطيع الحديث عن هذا. ما رأيك أن نكتشف بدلًا من ذلك لماذا تنفجر البراكين؟",
      more: "",
    },
  },
};

const SIMPLER_PREFIX: Record<Lang, string> = {
  fr: "En plus simple : ",
  ar: "بشكل أبسط: ",
};

/** Réponse adaptée à l'âge : courte pour les 6–8 ans, plus détaillée ensuite. */
export function answerFor(key: string, lang: Lang, age: number): string {
  const t = ANSWERS[key][lang];
  return age <= 8 || !t.more ? t.short : `${t.short} ${t.more}`;
}

export function simplerAnswerFor(key: string, lang: Lang): string {
  return SIMPLER_PREFIX[lang] + ANSWERS[key][lang].short.split(/(?<=[.!?؟])\s/)[0];
}

const ILLUSTRATIONS: Partial<Record<string, string>> = {
  volcano: "/mock/volcano.svg",
  space: "/mock/space.svg",
};

export function illustrationFor(key: string): string {
  return ILLUSTRATIONS[key] ?? "/mock/nature.svg";
}

export function ragSourceFor(rule: Rule): RagSource | null {
  if (rule.action !== "ALLOW" || rule.key === "generic") return null;
  return { book: "Éveil scientifique 5e", chapter: "La Terre et l'Univers", page: 42 };
}
