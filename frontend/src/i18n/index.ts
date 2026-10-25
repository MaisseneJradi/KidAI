import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import type { Lang } from "../api/types";
import ar from "./ar.json";
import fr from "./fr.json";

void i18n.use(initReactI18next).init({
  resources: { fr: { translation: fr }, ar: { translation: ar } },
  lng: "fr",
  fallbackLng: "fr",
  interpolation: { escapeValue: false },
});

/** Change la langue et bascule toute la page en RTL pour l'arabe. */
export function applyLanguage(lang: Lang) {
  void i18n.changeLanguage(lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
}

export default i18n;
