import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "soft" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-soleil text-encre shadow-[0_4px_0_#d9a21a] active:shadow-none active:translate-y-1",
  secondary: "bg-ciel text-encre shadow-[0_4px_0_#2b7fd4] active:shadow-none active:translate-y-1",
  soft: "bg-white text-encre border-2 border-encre/10 hover:border-ciel",
  danger: "bg-corail text-encre shadow-[0_4px_0_#d9544a] active:shadow-none active:translate-y-1",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

/** Bouton arrondi, cible tactile ≥ 48 px. */
export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-5 py-2 font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    />
  );
}
