import { motion, useReducedMotion, type TargetAndTransition } from "framer-motion";
import { useTranslation } from "react-i18next";

export type ChatyMood = "wave" | "think" | "wonder" | "reassure";

interface ChatyProps {
  mood?: ChatyMood;
  size?: number;
  className?: string;
}

const loop = (duration: number) => ({ duration, repeat: Infinity, ease: "easeInOut" as const });

// Mouvement global du corps selon l'humeur.
const bodyMotion: Record<ChatyMood, TargetAndTransition> = {
  wave: { y: [0, -4, 0], transition: loop(1.6) },
  think: { rotate: [0, -6, 0], transition: loop(2.4) },
  wonder: { y: [0, -12, 0], scale: [1, 1.04, 1], transition: loop(0.9) },
  reassure: { rotate: [-3, 3, -3], transition: loop(3) },
};

/** Chaty, mascotte originale de KidAI : un petit hibou-robot curieux. */
export function Chaty({ mood = "wave", size = 120, className }: ChatyProps) {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  const animate = (target: TargetAndTransition) => (reduce ? undefined : target);
  const happyEyes = mood === "reassure";
  const pupilOffset = mood === "think" ? { x: 4, y: -5 } : { x: 0, y: 0 };
  const pupilR = mood === "wonder" ? 10 : 8;

  return (
    <svg
      viewBox="0 0 200 200"
      width={size}
      height={size}
      role="img"
      aria-label={t("chaty.label")}
      data-mood={mood}
      className={className}
    >
      <motion.g
        animate={animate(bodyMotion[mood])}
        style={{ transformBox: "fill-box", transformOrigin: "50% 100%" }}
      >
        {/* Antenne : la lumière clignote quand Chaty réfléchit */}
        <line x1="100" y1="62" x2="100" y2="34" stroke="#24324A" strokeWidth="4" />
        <motion.circle
          cx="100"
          cy="28"
          r="8"
          fill="#FFC93C"
          stroke="#24324A"
          strokeWidth="3"
          initial={{ opacity: 1 }}
          animate={animate(
            mood === "think" ? { opacity: [1, 0.3, 1], transition: loop(0.8) } : { opacity: 1 },
          )}
        />

        {/* Aigrettes */}
        <path d="M52 78 L44 44 L76 64 Z" fill="#2B7FD4" />
        <path d="M148 78 L156 44 L124 64 Z" fill="#2B7FD4" />

        {/* Ailes (l'aile droite fait coucou) */}
        <ellipse cx="44" cy="134" rx="16" ry="32" fill="#2B7FD4" />
        <motion.ellipse
          cx="156"
          cy="134"
          rx="16"
          ry="32"
          fill="#2B7FD4"
          style={{ transformBox: "fill-box", transformOrigin: "50% 90%" }}
          animate={animate(
            mood === "wave"
              ? { rotate: [0, -35, 0, -35, 0], transition: loop(1.6) }
              : { rotate: 0 },
          )}
        />

        {/* Corps et ventre */}
        <ellipse cx="100" cy="122" rx="62" ry="64" fill="#4FA3F7" />
        <ellipse cx="100" cy="146" rx="36" ry="32" fill="#FFF8EC" />
        <path
          d="M84 140 q8 6 16 0 q8 6 16 0"
          fill="none"
          stroke="#4FA3F7"
          strokeWidth="3"
          strokeLinecap="round"
        />

        {/* Visière du robot */}
        <rect x="50" y="78" width="100" height="52" rx="26" fill="#24324A" />

        {/* Yeux */}
        {happyEyes ? (
          <>
            <path
              d="M64 104 q14 -14 28 0"
              fill="none"
              stroke="#3DD6A3"
              strokeWidth="6"
              strokeLinecap="round"
            />
            <path
              d="M108 104 q14 -14 28 0"
              fill="none"
              stroke="#3DD6A3"
              strokeWidth="6"
              strokeLinecap="round"
            />
          </>
        ) : (
          <>
            <circle cx="78" cy="104" r="17" fill="#FFF8EC" />
            <circle cx="122" cy="104" r="17" fill="#FFF8EC" />
            <circle cx={78 + pupilOffset.x} cy={104 + pupilOffset.y} r={pupilR} fill="#24324A" />
            <circle cx={122 + pupilOffset.x} cy={104 + pupilOffset.y} r={pupilR} fill="#24324A" />
            <circle cx={81 + pupilOffset.x} cy={100 + pupilOffset.y} r="3" fill="#FFF8EC" />
            <circle cx={125 + pupilOffset.x} cy={100 + pupilOffset.y} r="3" fill="#FFF8EC" />
          </>
        )}

        {/* Bec et joues */}
        <path d="M92 126 L108 126 L100 138 Z" fill="#FFC93C" />
        <circle cx="58" cy="136" r="7" fill="#FF7A6B" opacity="0.6" />
        <circle cx="142" cy="136" r="7" fill="#FF7A6B" opacity="0.6" />

        {/* Pattes */}
        <ellipse cx="80" cy="186" rx="13" ry="7" fill="#FFC93C" />
        <ellipse cx="120" cy="186" rx="13" ry="7" fill="#FFC93C" />
      </motion.g>

      {/* Étincelles d'émerveillement */}
      {mood === "wonder" && (
        <motion.g fill="#FFC93C" animate={animate({ opacity: [0, 1, 0], transition: loop(1.2) })}>
          <path d="M28 40 l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 Z" />
          <path d="M172 30 l3 8 l8 3 l-8 3 l-3 8 l-3 -8 l-8 -3 l8 -3 Z" />
          <path d="M180 92 l3 7 l7 3 l-7 3 l-3 7 l-3 -7 l-7 -3 l7 -3 Z" />
        </motion.g>
      )}

      {/* Cœur rassurant */}
      {mood === "reassure" && (
        <motion.path
          d="M168 60 c-6 -10 -22 -6 -18 6 c2 6 10 12 18 18 c8 -6 16 -12 18 -18 c4 -12 -12 -16 -18 -6 Z"
          fill="#FF7A6B"
          animate={animate({ y: [0, -8, 0], opacity: [0.7, 1, 0.7], transition: loop(2) })}
        />
      )}
    </svg>
  );
}
