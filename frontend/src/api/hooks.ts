import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/useAppStore";
import { api } from "./client";
import type { ChildInput, FeedbackInput, Lang } from "./types";

export const keys = {
  children: ["children"] as const,
  history: (childId: string) => ["history", childId] as const,
  image: (childId: string, messageId: string) => ["image", childId, messageId] as const,
  alerts: ["alerts"] as const,
  summary: (childId: string) => ["summary", childId] as const,
};

export function useChildren() {
  const signedIn = useAppStore((s) => s.token !== null);
  return useQuery({ queryKey: keys.children, queryFn: api.listChildren, enabled: signedIn });
}

export function useSaveChild() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id?: string; input: ChildInput }) =>
      id ? api.updateChild(id, input) : api.createChild(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.children }),
  });
}

export function useDeleteChild() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteChild,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.children }),
  });
}

export function useSendMessage(childId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ question, lang }: { question: string; lang: Lang }) =>
      api.sendMessage(childId, question, lang),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.history(childId) });
      qc.invalidateQueries({ queryKey: keys.alerts });
    },
  });
}

export function useSimplify(childId: string) {
  return useMutation({ mutationFn: (messageId: string) => api.simplify(childId, messageId) });
}

/** Interroge le statut de l'illustration toutes les secondes tant qu'elle est en préparation. */
export function useImage(childId: string, messageId: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.image(childId, messageId),
    queryFn: () => api.getImage(childId, messageId),
    enabled,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 1000 : false),
  });
}

export function useHistory(childId: string | null) {
  return useQuery({
    queryKey: keys.history(childId ?? ""),
    queryFn: () => api.history(childId!),
    enabled: !!childId,
  });
}

export function useAuth(mode: "login" | "register") {
  const qc = useQueryClient();
  const setToken = useAppStore((s) => s.setToken);
  return useMutation({
    mutationFn: ({ email, password, pin }: { email: string; password: string; pin: string }) =>
      mode === "login" ? api.login(email, password) : api.register(email, password, pin),
    onSuccess: (token) => {
      qc.clear();
      setToken(token.access_token);
    },
  });
}

export function useVerifyPin() {
  return useMutation({ mutationFn: api.verifyPin });
}

export function useAlerts(enabled: boolean) {
  return useQuery({ queryKey: keys.alerts, queryFn: api.alerts, enabled });
}

export function useSummary(childId: string | null) {
  return useQuery({
    queryKey: keys.summary(childId ?? ""),
    queryFn: () => api.summary(childId!),
    enabled: !!childId,
  });
}

export function useFeedback() {
  return useMutation({ mutationFn: (input: FeedbackInput) => api.feedback(input) });
}

export function useDeleteChildData() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteChildData,
    onSuccess: () => qc.invalidateQueries(),
  });
}
