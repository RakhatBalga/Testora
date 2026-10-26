/** Badge colours (background + text) for a band score; null = not graded. */
export function bandBadgeClass(band: number | null): string {
  if (band === null) return "bg-slate-100 text-slate-500";
  if (band >= 7) return "bg-emerald-50 text-emerald-700";
  if (band >= 5.5) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

/** Text-only colour for a band score. */
export function bandTextClass(band: number | null): string {
  if (band === null) return "text-slate-500";
  if (band >= 7) return "text-emerald-600";
  if (band >= 5.5) return "text-amber-600";
  return "text-red-600";
}

/** Round to the nearest half band (IELTS granularity). */
export function roundHalf(n: number): number {
  return Math.round(n * 2) / 2;
}
