import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { useAuth } from "../api/hooks";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Chaty } from "../components/Chaty";

const fieldClass = "min-h-12 w-full rounded-2xl border-2 border-encre/15 bg-white px-3";

function errorKey(error: unknown, mode: "login" | "register"): string {
  if (!(error instanceof ApiError)) return "auth.errorGeneric";
  if (error.status === 401) return "auth.errorLogin";
  if (error.status === 409) return "auth.errorExists";
  if (error.status === 422) return mode === "login" ? "auth.errorLogin" : "auth.errorInvalid";
  return "auth.errorGeneric";
}

/** Connexion / création du compte parent (préalable à tout l'usage de l'appareil). */
export default function Connexion() {
  const { t } = useTranslation();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pin, setPin] = useState("");
  const auth = useAuth(mode);
  const demo = import.meta.env.VITE_USE_MOCKS !== "false";

  const submit = (e: FormEvent) => {
    e.preventDefault();
    auth.mutate({ email, password, pin });
  };

  const switchMode = () => {
    auth.reset();
    setMode(mode === "login" ? "register" : "login");
  };

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center gap-5 px-4 py-8">
      <Chaty mood="wave" size={120} />
      <div className="text-center">
        <h1 className="text-3xl font-bold">{t("auth.title")}</h1>
        <p className="mt-2">{t("auth.subtitle")}</p>
      </div>

      <Card className="w-full">
        <form onSubmit={submit} className="flex flex-col gap-4">
          <h2 className="text-xl font-semibold">
            {t(mode === "login" ? "auth.login" : "auth.register")}
          </h2>
          <label className="flex flex-col gap-1">
            {t("auth.email")}
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={fieldClass}
              dir="ltr"
            />
          </label>
          <label className="flex flex-col gap-1">
            {t("auth.password")}
            <input
              type="password"
              required
              minLength={mode === "register" ? 8 : undefined}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={fieldClass}
              dir="ltr"
            />
            {mode === "register" && (
              <span className="text-sm text-encre/80">{t("auth.passwordHint")}</span>
            )}
          </label>
          {mode === "register" && (
            <label className="flex flex-col gap-1">
              {t("auth.pin")}
              <input
                type="password"
                required
                inputMode="numeric"
                pattern="\d{4}"
                maxLength={4}
                autoComplete="off"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
                className={`${fieldClass} tracking-[0.5em]`}
                dir="ltr"
              />
              <span className="text-sm text-encre/80">{t("auth.pinHelp")}</span>
            </label>
          )}
          {auth.isError && (
            <p role="alert" className="font-semibold">
              ⚠️ {t(errorKey(auth.error, mode))}
            </p>
          )}
          <Button type="submit" disabled={auth.isPending}>
            {t(mode === "login" ? "auth.login" : "auth.register")}
          </Button>
        </form>
        <button
          type="button"
          onClick={switchMode}
          className="mt-4 min-h-12 w-full font-semibold underline underline-offset-4"
        >
          {t(mode === "login" ? "auth.toRegister" : "auth.toLogin")}
        </button>
      </Card>

      {demo && <p className="text-center text-sm text-encre/80">{t("auth.demoHint")}</p>}
    </main>
  );
}
