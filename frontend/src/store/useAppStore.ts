import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { Lang } from "../api/types";
import type { Band } from "../lib/ageBand";

export type ThemeChoice = "auto" | Band;

interface AppState {
  /** JWT du parent connecté sur cet appareil. */
  token: string | null;
  currentChildId: string | null;
  lang: Lang;
  sounds: boolean;
  theme: ThemeChoice;
  /** Jamais persisté : l'espace parent se reverrouille à chaque visite. */
  parentUnlocked: boolean;
  setToken: (token: string | null) => void;
  logout: () => void;
  selectChild: (id: string | null, lang?: Lang) => void;
  setLang: (lang: Lang) => void;
  setSounds: (on: boolean) => void;
  setTheme: (theme: ThemeChoice) => void;
  setParentUnlocked: (unlocked: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      token: null,
      currentChildId: null,
      lang: "fr",
      sounds: false,
      theme: "auto",
      parentUnlocked: false,
      setToken: (token) => set({ token }),
      logout: () => set({ token: null, currentChildId: null, parentUnlocked: false }),
      selectChild: (id, lang) => set(lang ? { currentChildId: id, lang } : { currentChildId: id }),
      setLang: (lang) => set({ lang }),
      setSounds: (sounds) => set({ sounds }),
      setTheme: (theme) => set({ theme }),
      setParentUnlocked: (parentUnlocked) => set({ parentUnlocked }),
    }),
    {
      name: "kidai-app",
      storage: createJSONStorage(() => localStorage),
      partialize: ({ token, currentChildId, lang, sounds, theme }) => ({
        token,
        currentChildId,
        lang,
        sounds,
        theme,
      }),
    },
  ),
);
