import type {
  Alert,
  Child,
  ChildInput,
  FeedbackInput,
  HistoryItem,
  ImageResponse,
  Lang,
  MessageResponse,
  Summary,
  Token,
} from "./types";
import { useAppStore } from "../store/useAppStore";

export class ApiError extends Error {
  constructor(public status: number) {
    super(`API error ${status}`);
  }
}

// Le navigateur n'appelle que notre API FastAPI (jamais un modèle directement).
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAppStore.getState().token;
  const res = await fetch(new URL(path, window.location.origin), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    // Session expirée ou invalide : retour à l'écran de connexion.
    if (res.status === 401 && token) useAppStore.getState().logout();
    throw new ApiError(res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  register: (email: string, password: string, pin: string) =>
    request<Token>("/api/auth/parent/register", {
      method: "POST",
      body: json({ email, password, pin }),
    }),
  login: (email: string, password: string) =>
    request<Token>("/api/auth/parent/login", { method: "POST", body: json({ email, password }) }),
  verifyPin: (pin: string) =>
    request<{ ok: boolean }>("/api/auth/parent/pin", { method: "POST", body: json({ pin }) }),

  listChildren: () => request<Child[]>("/api/children"),
  createChild: (input: ChildInput) =>
    request<Child>("/api/children", { method: "POST", body: json(input) }),
  updateChild: (id: string, input: Partial<ChildInput>) =>
    request<Child>(`/api/children/${id}`, { method: "PATCH", body: json(input) }),
  deleteChild: (id: string) => request<void>(`/api/children/${id}`, { method: "DELETE" }),

  sendMessage: (childId: string, question: string, lang: Lang) =>
    request<MessageResponse>(`/api/chat/${childId}/messages`, {
      method: "POST",
      body: json({ question, lang }),
    }),
  getImage: (childId: string, messageId: string) =>
    request<ImageResponse>(`/api/chat/${childId}/messages/${messageId}/image`),
  simplify: (childId: string, messageId: string) =>
    request<MessageResponse>(`/api/chat/${childId}/messages/${messageId}/simplify`, {
      method: "POST",
    }),
  history: (childId: string) => request<HistoryItem[]>(`/api/chat/${childId}/history`),

  alerts: () => request<Alert[]>("/api/parent/alerts"),
  summary: (childId: string) => request<Summary>(`/api/parent/summary/${childId}`),
  feedback: (input: FeedbackInput) =>
    request<{ ok: boolean }>("/api/parent/feedback", { method: "POST", body: json(input) }),
  deleteChildData: (childId: string) =>
    request<void>(`/api/parent/children/${childId}/data`, { method: "DELETE" }),
};
