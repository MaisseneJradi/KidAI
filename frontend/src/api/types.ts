// Types du contrat d'API (cahier des charges, section 14).

export const ACTIONS = ["ALLOW", "REWRITE", "REDIRECT", "ASK_ADULT", "BLOCK"] as const;
export type Action = (typeof ACTIONS)[number];

export type Lang = "fr" | "ar";
export type CautionLevel = "standard" | "renforce";
export type ImageStatus = "pending" | "ready" | "none" | "failed";

export const TOPICS = ["sciences", "espace", "animaux", "histoire", "corps", "autre"] as const;
export type Topic = (typeof TOPICS)[number];

export const SEXES = ["fille", "garcon", "non_precise"] as const;
export type Sex = (typeof SEXES)[number];

export const INTERESTS = [
  "sciences",
  "espace",
  "animaux",
  "histoire",
  "corps",
  "sport",
  "musique",
  "art",
] as const;
export type Interest = (typeof INTERESTS)[number];

/** Besoins d'adaptation (pas de données médicales libres, NF-06). */
export const NEEDS = [
  "dyslexie",
  "deficience_visuelle",
  "attention",
  "deficience_auditive",
] as const;
export type Need = (typeof NEEDS)[number];

export interface Child {
  id: string;
  first_name: string;
  avatar: string;
  /** Date ISO (AAAA-MM-JJ), chiffrée côté serveur. */
  birth_date: string;
  /** Calculé par le serveur à partir de la date de naissance. */
  age: number;
  sex: Sex;
  grade: string;
  lang: Lang;
  caution_level: CautionLevel;
  interests: Interest[];
  needs: Need[];
}

export type ChildInput = Omit<Child, "id" | "age">;

export interface Token {
  access_token: string;
  token_type: "bearer";
}

export interface RagSource {
  book: string;
  chapter: string;
  page: number;
}

export interface MessageResponse {
  message_id: string;
  text: string;
  action: Action;
  lang: Lang;
  rag_source: RagSource | null;
  image_status: ImageStatus;
  safety: { input_risk: "safe" | "controversial" | "unsafe"; output_check: "pass" | "fail" };
}

export interface ImageResponse {
  status: ImageStatus;
  url: string | null;
}

export interface HistoryItem {
  message_id: string;
  question: string;
  answer: string;
  action: Action;
  topic: Topic;
  created_at: string;
}

export interface Alert {
  id: string;
  child_id: string;
  message_id: string;
  type: "ASK_ADULT";
  question: string;
  seen: boolean;
  created_at: string;
}

export interface Summary {
  child_id: string;
  total_questions: number;
  by_action: Record<Action, number>;
  by_topic: Partial<Record<Topic, number>>;
}

export interface FeedbackInput {
  message_id: string;
  rating: "up" | "down";
  comment?: string;
}

/** Actions pour lesquelles une illustration et le bouton « Plus simple » ont du sens. */
export const ANSWER_ACTIONS: readonly Action[] = ["ALLOW", "REWRITE", "REDIRECT"];
