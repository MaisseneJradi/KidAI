import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { useChildren } from "./api/hooks";
import { ChildLayout } from "./components/ChildLayout";
import { applyLanguage } from "./i18n";
import { bandForAge } from "./lib/ageBand";
import Accueil from "./pages/Accueil";
import Badges from "./pages/Badges";
import Chat from "./pages/Chat";
import Connexion from "./pages/Connexion";
import Decouvertes from "./pages/Decouvertes";
import Parent from "./pages/Parent";
import Reglages from "./pages/Reglages";
import { useAppStore } from "./store/useAppStore";

/** Applique la langue (et le RTL), le thème d'âge et les besoins d'adaptation à toute la page. */
function useGlobalAppearance() {
  const lang = useAppStore((s) => s.lang);
  const theme = useAppStore((s) => s.theme);
  const childId = useAppStore((s) => s.currentChildId);
  const child = useChildren().data?.find((c) => c.id === childId);
  const age = child?.age;
  const needs = child?.needs.join(" ") ?? "";

  useEffect(() => applyLanguage(lang), [lang]);

  useEffect(() => {
    const band = theme !== "auto" ? theme : age !== undefined ? bandForAge(age) : "middle";
    document.documentElement.dataset.band = band;
  }, [theme, age]);

  useEffect(() => {
    document.documentElement.dataset.needs = needs;
  }, [needs]);
}

export default function App() {
  useGlobalAppearance();
  const token = useAppStore((s) => s.token);

  if (!token) return <Connexion />;

  return (
    <Routes>
      <Route path="/" element={<Accueil />} />
      <Route path="/parent" element={<Parent />} />
      <Route element={<ChildLayout />}>
        <Route path="/chat" element={<Chat />} />
        <Route path="/decouvertes" element={<Decouvertes />} />
        <Route path="/badges" element={<Badges />} />
        <Route path="/reglages" element={<Reglages />} />
      </Route>
      <Route path="*" element={<Accueil />} />
    </Routes>
  );
}
