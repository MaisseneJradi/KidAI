import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

type From = "chaty" | "child" | "gentle";

const styles: Record<From, string> = {
  chaty: "bg-white self-start rounded-ss-md",
  gentle: "bg-white self-start rounded-ss-md border-2 border-menthe",
  child: "bg-ciel self-end rounded-se-md",
};

/** Bulle de dialogue qui « rebondit » en apparaissant. */
export function Bubble({ from, children }: { from: From; children: ReactNode }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 12, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 380, damping: 22 }}
      className={`max-w-[85%] p-4 text-encre shadow-sm ${styles[from]}`}
      style={{ borderRadius: "var(--radius-bulle)" }}
      data-from={from}
    >
      {children}
    </motion.div>
  );
}
