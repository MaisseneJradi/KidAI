import { AVATARS } from "../lib/avatars";

const colors = ["bg-soleil", "bg-menthe", "bg-corail", "bg-ciel"];

interface AvatarProps {
  emoji: string;
  size?: "md" | "lg";
}

export function Avatar({ emoji, size = "md" }: AvatarProps) {
  const color = colors[Math.max(0, AVATARS.indexOf(emoji)) % colors.length];
  const dims = size === "lg" ? "h-24 w-24 text-5xl" : "h-12 w-12 text-2xl";
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-full ${color} ${dims}`}
    >
      {emoji}
    </span>
  );
}
