import { useTranslation } from "react-i18next";
import { useHistory } from "../api/hooks";
import { Badge } from "../components/Badge";
import { BADGES, earnedBadges } from "../lib/badges";
import { useAppStore } from "../store/useAppStore";

export default function Badges() {
  const { t } = useTranslation();
  const childId = useAppStore((s) => s.currentChildId);
  const history = useHistory(childId).data ?? [];
  const earned = earnedBadges(history);

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-3xl font-bold">{t("badges.title")}</h1>
      <p>{t("badges.intro")}</p>
      <p className="flex items-center gap-2 text-xl font-semibold">
        <span aria-hidden="true">⭐</span>
        {t("badges.stars", { count: history.length })}
      </p>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {BADGES.map((b) => (
          <Badge
            key={b.id}
            icon={b.icon}
            name={t(`badges.items.${b.id}.name`)}
            description={t(`badges.items.${b.id}.desc`)}
            unlocked={earned.has(b.id)}
          />
        ))}
      </ul>
    </div>
  );
}
