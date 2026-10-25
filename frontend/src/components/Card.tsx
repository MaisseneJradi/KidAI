import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={`rounded-3xl bg-white p-5 shadow-[0_4px_0_rgba(36,50,74,0.08)] ${className}`}
      {...props}
    />
  );
}
