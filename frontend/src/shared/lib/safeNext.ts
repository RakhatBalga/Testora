/**
 * Validate a post-login `?next=` target. Only same-site relative paths are
 * allowed: protocol-relative (`//host`), backslash tricks (`/\host`), absolute
 * URLs and control characters are rejected and fall back to `fallback`.
 */
export function safeNext(next: string | null | undefined, fallback = "/"): string {
  if (!next || !next.startsWith("/")) return fallback;
  if (next.startsWith("//") || next.startsWith("/\\")) return fallback;
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f\\]/.test(next)) return fallback;
  try {
    const base = "http://safe-next.invalid";
    const url = new URL(next, base);
    if (url.origin !== base) return fallback;
  } catch {
    return fallback;
  }
  return next;
}
