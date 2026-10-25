import type { ComponentProps } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { Lang } from "../api/types";
import { Card } from "../components/Card";
import { useAppStore, type ThemeChoice } from "../store/useAppStore";

const LANGS: Lang[] = ["fr", "ar"];
const THEMES: ThemeChoice[] = ["auto", "small", "middle", "teen"];

function Choice({ selected, ...props }: { selected: boolean } & ComponentProps<"button">) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={`min-h-12 rounded-full border-2 px-4 font-semibold ${
        selected ? "border-encre bg-soleil" : "border-encre/15 bg-white"
      }`}
      {...props}
    />
  );
}

export default function Reglages() {
  const { t } = useTranslation();
  const { lang, setLang, sounds, setSounds, theme, setTheme } = useAppStore();

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-3xl font-bold">{t("settings.title")}</h1>

      <Card aria-labelledby="set-lang">
        <h2 id="set-lang" className="mb-3 text-xl font-semibold">
          {t("settings.language")}
        </h2>
        <div className="flex flex-wrap gap-2">
          {LANGS.map((l) => (
            <Choice key={l} selected={lang === l} onClick={() => setLang(l)} lang={l}>
              {t(`languages.${l}`)}
            </Choice>
          ))}
        </div>
      </Card>

      <Card aria-labelledby="set-sounds">
        <label className="flex min-h-12 cursor-pointer items-center justify-between gap-4">
          <span>
            <span id="set-sounds" className="block text-xl font-semibold">
              {t("settings.sounds")}
            </span>
            <span className="text-sm text-encre/80">{t("settings.soundsHint")}</span>
          </span>
          <input
            type="checkbox"
            role="switch"
            checked={sounds}
            onChange={(e) => setSounds(e.target.checked)}
            className="h-7 w-7 accent-ciel-fonce"
          />
        </label>
      </Card>

      <Card aria-labelledby="set-theme">
        <h2 id="set-theme" className="mb-3 text-xl font-semibold">
          {t("settings.theme")}
        </h2>
        <div className="flex flex-wrap gap-2">
          {THEMES.map((th) => (
            <Choice key={th} selected={theme === th} onClick={() => setTheme(th)}>
              {t(`settings.themes.${th}`)}
            </Choice>
          ))}
        </div>
      </Card>

      <Link
        to="/parent"
        className="flex min-h-12 items-center gap-2 self-start rounded-full px-2 font-semibold underline-offset-4 hover:underline"
      >
        <span aria-hidden="true">🔐</span>
        {t("settings.parent")}
      </Link>
    </div>
  );
}
