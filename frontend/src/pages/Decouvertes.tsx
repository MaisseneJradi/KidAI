import { useTranslation } from "react-i18next";
import { useHistory } from "../api/hooks";
import { TOPICS, type HistoryItem, type Topic } from "../api/types";
import { Card } from "../components/Card";
import { Chaty } from "../components/Chaty";
import { TOPIC_ICONS } from "../lib/badges";
import { useAppStore } from "../store/useAppStore";

export default function Decouvertes() {
  const { t } = useTranslation();
  const childId = useAppStore((s) => s.currentChildId);
  const { data: history, isLoading } = useHistory(childId);

  const byTopic = new Map<Topic, HistoryItem[]>();
  for (const item of history ?? []) {
    byTopic.set(item.topic, [...(byTopic.get(item.topic) ?? []), item]);
  }

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-3xl font-bold">{t("discoveries.title")}</h1>
      {isLoading && <p>{t("common.loading")}</p>}
      {history?.length === 0 && (
        <div className="flex flex-col items-center gap-3 text-center">
          <Chaty mood="wave" size={110} />
          <p>{t("discoveries.empty")}</p>
        </div>
      )}
      {TOPICS.filter((topic) => byTopic.has(topic)).map((topic) => (
        <section key={topic} aria-labelledby={`topic-${topic}`}>
          <h2 id={`topic-${topic}`} className="mb-2 flex items-center gap-2 text-xl font-semibold">
            <span aria-hidden="true">{TOPIC_ICONS[topic]}</span>
            {t(`topics.${topic}`)}
          </h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {byTopic.get(topic)!.map((item) => (
              <li key={item.message_id}>
                <Card className="h-full">
                  <p className="font-semibold">{item.question}</p>
                  <p className="mt-2 line-clamp-3 text-sm text-encre/80">{item.answer}</p>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
