export type Band = "small" | "middle" | "teen";

/** Tranches d'âge du cahier des charges : 6–8, 9–11, 12–14 ans. */
export function bandForAge(age: number): Band {
  if (age <= 8) return "small";
  if (age <= 11) return "middle";
  return "teen";
}
