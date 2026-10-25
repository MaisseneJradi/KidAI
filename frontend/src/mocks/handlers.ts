import { delay, http, HttpResponse } from "msw";
import type {
  Action,
  Alert,
  Child,
  ChildInput,
  FeedbackInput,
  HistoryItem,
  Lang,
  MessageResponse,
} from "../api/types";
import { ACTIONS, ANSWER_ACTIONS } from "../api/types";
import { ageFromBirthDate } from "../lib/age";
import {
  answerFor,
  classify,
  IMAGE_DELAY_MS,
  illustrationFor,
  initialChildren,
  MOCK_PIN,
  MOCK_TOKEN,
  ragSourceFor,
  simplerAnswerFor,
  type StoredChild,
} from "./data";

interface StoredMessage extends HistoryItem {
  child_id: string;
  key: string;
  lang: Lang;
  createdMs: number;
}

const db = {
  children: [] as StoredChild[],
  messages: [] as StoredMessage[],
  alerts: [] as Alert[],
  feedbacks: [] as FeedbackInput[],
  seq: 0,
};

// La base simulée survit au rechargement de la page (comme le ferait un vrai backend).
const STORAGE_KEY = "kidai-mock-db-v2";

function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch {
    // Stockage indisponible : la base reste en mémoire.
  }
}

function load(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    Object.assign(db, JSON.parse(raw));
    return true;
  } catch {
    return false;
  }
}

export function resetMockDb() {
  db.children = initialChildren.map((c) => ({ ...c }));
  db.messages = [];
  db.alerts = [];
  db.feedbacks = [];
  db.seq = 0;
  save();
}
if (!load()) resetMockDb();

const nextId = (prefix: string) => `${prefix}_${String(++db.seq).padStart(4, "0")}`;
const notFound = () => HttpResponse.json({ detail: "Not found" }, { status: 404 });
// Comme le serveur : l'âge est calculé, jamais stocké.
const withAge = (c: StoredChild): Child => ({ ...c, age: ageFromBirthDate(c.birth_date) });
const token = () => HttpResponse.json({ access_token: MOCK_TOKEN, token_type: "bearer" });

function toResponse(m: StoredMessage, text: string): MessageResponse {
  const withImage = ANSWER_ACTIONS.includes(m.action);
  return {
    message_id: m.message_id,
    text,
    action: m.action,
    lang: m.lang,
    rag_source: ragSourceFor(classify(m.question)),
    image_status: withImage ? "pending" : "none",
    safety: {
      input_risk: m.action === "ALLOW" ? "safe" : m.action === "BLOCK" ? "unsafe" : "controversial",
      output_check: "pass",
    },
  };
}

export const handlers = [
  // Mode démo : n'importe quel email / mot de passe est accepté.
  http.post("/api/auth/parent/register", () => token()),
  http.post("/api/auth/parent/login", () => token()),

  http.post("/api/auth/parent/pin", async ({ request }) => {
    const { pin } = (await request.json()) as { pin: string };
    return pin === MOCK_PIN
      ? HttpResponse.json({ ok: true })
      : HttpResponse.json({ detail: "PIN incorrect" }, { status: 403 });
  }),

  http.get("/api/children", () => HttpResponse.json(db.children.map(withAge))),

  http.post("/api/children", async ({ request }) => {
    const child = { id: nextId("child"), ...((await request.json()) as ChildInput) };
    db.children.push(child);
    save();
    return HttpResponse.json(withAge(child), { status: 201 });
  }),

  http.patch("/api/children/:id", async ({ params, request }) => {
    const child = db.children.find((c) => c.id === params.id);
    if (!child) return notFound();
    Object.assign(child, (await request.json()) as Partial<ChildInput>);
    save();
    return HttpResponse.json(withAge(child));
  }),

  http.delete("/api/children/:id", ({ params }) => {
    db.children = db.children.filter((c) => c.id !== params.id);
    db.messages = db.messages.filter((m) => m.child_id !== params.id);
    db.alerts = db.alerts.filter((a) => a.child_id !== params.id);
    save();
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/chat/:childId/messages", async ({ params, request }) => {
    const child = db.children.find((c) => c.id === params.childId);
    if (!child) return notFound();
    const { question, lang } = (await request.json()) as { question: string; lang: Lang };
    const rule = classify(question);
    await delay(500); // laisse le temps de voir « Chaty réfléchit… »

    const message: StoredMessage = {
      message_id: nextId("msg"),
      child_id: child.id,
      question,
      answer: answerFor(rule.key, lang, ageFromBirthDate(child.birth_date)),
      action: rule.action,
      topic: rule.topic,
      key: rule.key,
      lang,
      created_at: new Date().toISOString(),
      createdMs: Date.now(),
    };
    db.messages.push(message);

    if (rule.action === "ASK_ADULT") {
      db.alerts.unshift({
        id: nextId("alert"),
        child_id: child.id,
        message_id: message.message_id,
        type: "ASK_ADULT",
        question,
        seen: false,
        created_at: message.created_at,
      });
    }
    save();
    return HttpResponse.json(toResponse(message, message.answer));
  }),

  http.get("/api/chat/:childId/messages/:id/image", ({ params }) => {
    const m = db.messages.find((x) => x.message_id === params.id);
    if (!m) return notFound();
    if (!ANSWER_ACTIONS.includes(m.action)) return HttpResponse.json({ status: "none", url: null });
    const ready = Date.now() - m.createdMs >= IMAGE_DELAY_MS;
    return HttpResponse.json(
      ready ? { status: "ready", url: illustrationFor(m.key) } : { status: "pending", url: null },
    );
  }),

  http.post("/api/chat/:childId/messages/:id/simplify", async ({ params }) => {
    const m = db.messages.find((x) => x.message_id === params.id);
    if (!m) return notFound();
    await delay(300);
    return HttpResponse.json(toResponse(m, simplerAnswerFor(m.key, m.lang)));
  }),

  http.get("/api/chat/:childId/history", ({ params }) =>
    HttpResponse.json(
      db.messages
        .filter((m) => m.child_id === params.childId)
        .map(({ message_id, question, answer, action, topic, created_at }) => ({
          message_id,
          question,
          answer,
          action,
          topic,
          created_at,
        }))
        .reverse(),
    ),
  ),

  http.get("/api/parent/alerts", () => HttpResponse.json(db.alerts)),

  http.get("/api/parent/summary/:childId", ({ params }) => {
    const msgs = db.messages.filter((m) => m.child_id === params.childId);
    const by_action = Object.fromEntries(ACTIONS.map((a) => [a, 0])) as Record<Action, number>;
    const by_topic: Record<string, number> = {};
    for (const m of msgs) {
      by_action[m.action] += 1;
      by_topic[m.topic] = (by_topic[m.topic] ?? 0) + 1;
    }
    return HttpResponse.json({
      child_id: params.childId,
      total_questions: msgs.length,
      by_action,
      by_topic,
    });
  }),

  http.post("/api/parent/feedback", async ({ request }) => {
    db.feedbacks.push((await request.json()) as FeedbackInput);
    save();
    return HttpResponse.json({ ok: true }, { status: 201 });
  }),

  http.delete("/api/parent/children/:childId/data", ({ params }) => {
    db.messages = db.messages.filter((m) => m.child_id !== params.childId);
    db.alerts = db.alerts.filter((a) => a.child_id !== params.childId);
    save();
    return new HttpResponse(null, { status: 204 });
  }),
];
