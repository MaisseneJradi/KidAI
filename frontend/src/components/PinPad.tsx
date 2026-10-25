import { useState } from "react";
import { useTranslation } from "react-i18next";

const PIN_LENGTH = 4;
const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

interface PinPadProps {
  onComplete: (pin: string) => void;
  error?: boolean;
  disabled?: boolean;
}

/** Clavier numérique à gros boutons pour le code PIN parent. */
export function PinPad({ onComplete, error, disabled }: PinPadProps) {
  const { t } = useTranslation();
  const [pin, setPin] = useState("");

  const press = (key: string) => {
    if (key === "⌫") return setPin((p) => p.slice(0, -1));
    const next = (pin + key).slice(0, PIN_LENGTH);
    setPin(next);
    if (next.length === PIN_LENGTH) {
      onComplete(next);
      setPin("");
    }
  };

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="flex gap-3" aria-hidden="true">
        {Array.from({ length: PIN_LENGTH }, (_, i) => (
          <span
            key={i}
            className={`h-5 w-5 rounded-full border-2 border-encre ${i < pin.length ? "bg-encre" : ""}`}
          />
        ))}
      </div>
      {error && (
        <p role="alert" className="font-semibold text-encre">
          ⚠️ {t("parent.pinError")}
        </p>
      )}
      <div className="grid grid-cols-3 gap-3" dir="ltr">
        {KEYS.map((key, i) =>
          key === "" ? (
            <span key={i} />
          ) : (
            <button
              key={i}
              type="button"
              disabled={disabled}
              onClick={() => press(key)}
              aria-label={key === "⌫" ? t("parent.erase") : t("parent.pinDigit", { digit: key })}
              className="h-16 w-16 rounded-full bg-white text-2xl font-semibold shadow-[0_4px_0_rgba(36,50,74,0.1)] active:translate-y-1 active:shadow-none disabled:opacity-50"
            >
              {key}
            </button>
          ),
        )}
      </div>
    </div>
  );
}
