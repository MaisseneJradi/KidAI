import type { HistoryItem, Topic } from "../api/types";

interface BadgeDef {
  id: string;
  icon: string;
  earned: (total: number, count: (topic: Topic) => number) => boolean;
}

// Badges de curiosité : aucun classement, aucune série à maintenir (NF-10).
export const BADGES: BadgeDef[] = [
  { id: "first", icon: "🌱", earned: (total) => total >= 1 },
  { id: "curious", icon: "🔭", earned: (total) => total >= 5 },
  { id: "scientist", icon: "🧪", earned: (_, n) => n("sciences") >= 3 },
  { id: "astronaut", icon: "🚀", earned: (_, n) => n("espace") >= 2 },
  { id: "naturalist", icon: "🦋", earned: (_, n) => n("animaux") >= 2 },
  { id: "body", icon: "🩺", earned: (_, n) => n("corps") >= 2 },
];

export function earnedBadges(history: HistoryItem[]): Set<string> {
  const count = (topic: Topic) => history.filter((h) => h.topic === topic).length;
  return new Set(BADGES.filter((b) => b.earned(history.length, count)).map((b) => b.id));
}

export const TOPIC_ICONS: Record<Topic, string> = {
  sciences: "🔬",
  espace: "🪐",
  animaux: "🐾",
  histoire: "🏛️",
  corps: "❤️",
  autre: "✨",
};
