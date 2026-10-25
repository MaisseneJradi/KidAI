import { useTranslation } from "react-i18next";

interface BadgeProps {
  icon: string;
  name: string;
  description: string;
  unlocked: boolean;
}

/** Badge de curiosité. L'état est écrit en toutes lettres, pas seulement en couleur. */
export function Badge({ icon, name, description, unlocked }: BadgeProps) {
  const { t } = useTranslation();
  return (
    <li
      className={`flex flex-col items-center gap-2 rounded-3xl p-4 text-center ${
        unlocked ? "bg-white shadow-[0_4px_0_rgba(36,50,74,0.08)]" : "bg-encre/5"
      }`}
      data-unlocked={unlocked}
    >
      <span
        aria-hidden="true"
        className={`flex h-16 w-16 items-center justify-center rounded-full text-3xl ${
          unlocked ? "bg-soleil" : "bg-encre/10 grayscale"
        }`}
      >
        {unlocked ? icon : "🔒"}
      </span>
      <span className="font-semibold">{name}</span>
      <span className="text-sm text-encre/80">{description}</span>
      <span className={`text-sm font-semibold ${unlocked ? "text-encre" : "text-encre/70"}`}>
        {unlocked ? `✓ ${t("badges.unlocked")}` : t("badges.locked")}
      </span>
    </li>
  );
}
