/** Locale date, or `fallback` when there is no value. */
export function formatDate(value: string | null, fallback = "No date"): string {
  if (!value) return fallback;
  return new Date(value).toLocaleDateString();
}

/** "5 Mar 2026" style date; "—" when missing. */
export function formatShortDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

/** "1m 5s" / "42s"; null when the duration is unknown. */
export function formatDuration(seconds: number | null): string | null {
  if (seconds == null) return null;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
