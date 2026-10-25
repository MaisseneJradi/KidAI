export const MIN_AGE = 6;
export const MAX_AGE = 14;

/** Âge en années révolues à partir d'une date ISO (AAAA-MM-JJ). */
export function ageFromBirthDate(birthDate: string, today = new Date()): number {
  const [y, m, d] = birthDate.split("-").map(Number);
  const hadBirthday =
    today.getMonth() + 1 > m || (today.getMonth() + 1 === m && today.getDate() >= d);
  return today.getFullYear() - y - (hadBirthday ? 0 : 1);
}

/** Bornes du sélecteur de date pour un enfant de 6 à 14 ans. */
export function birthDateBounds(today = new Date()): { min: string; max: string } {
  const iso = (date: Date) => date.toISOString().slice(0, 10);
  const max = new Date(today.getFullYear() - MIN_AGE, today.getMonth(), today.getDate());
  const min = new Date(today.getFullYear() - MAX_AGE - 1, today.getMonth(), today.getDate() + 1);
  return { min: iso(min), max: iso(max) };
}
