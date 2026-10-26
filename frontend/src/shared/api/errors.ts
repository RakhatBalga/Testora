import { clearStoredAuth } from "./token";

/** The request never produced an HTTP response: offline, DNS, CORS-less 5xx
 *  from a sleeping host, or our own timeout. Pages show it with a retry. */
export class NetworkError extends Error {
  readonly kind: "timeout" | "network" | "unavailable";

  constructor(kind: "timeout" | "network" | "unavailable") {
    super(
      kind === "timeout"
        ? "The server is taking too long to respond. It may be waking up (this can take up to a minute). Please try again."
        : kind === "unavailable"
          ? "The server is temporarily unavailable or waking up (this can take up to a minute). Please try again."
          : "Can't reach the server. Check your connection, or wait a moment if it is waking up, and try again.",
    );
    this.name = "NetworkError";
    this.kind = kind;
  }
}

export function isNetworkError(error: unknown): error is NetworkError {
  return error instanceof NetworkError;
}

/**
 * Global handler for an expired/invalid session. Clears stored credentials and
 * bounces the user to /login (preserving where they were) instead of leaving
 * them stuck on a screen full of failed requests. Safe to call repeatedly.
 */
export function handleUnauthorized(): void {
  if (typeof window === "undefined") return;
  clearStoredAuth();
  const { pathname, search } = window.location;
  // The OAuth callback URL carries a single-use code; replaying it after
  // login would only produce a confusing error.
  if (pathname !== "/login" && !pathname.startsWith("/auth/google")) {
    const next = encodeURIComponent(pathname + search);
    // Full navigation on purpose: resets all in-memory state of a dead session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign(`/login?next=${next}`);
  }
}

/** FastAPI errors carry `detail` as either a string or, for validation
 *  failures (422), an array of {loc, msg} objects. Render both as readable
 *  text instead of the dreaded "[object Object]". */
export function detailToMessage(detail: unknown, fallback = "Request failed"): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const { code, message, resets_at } = detail as { code?: string; message?: string; resets_at?: string };
    if (typeof message === "string" && message.trim()) {
      const reset = typeof resets_at === "string" ? new Date(resets_at) : null;
      if (code === "ai_daily_limit" && reset && Number.isFinite(reset.getTime())) {
        return `${message} Available again at ${reset.toLocaleString()} (your local time).`;
      }
      return message;
    }
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const { loc, msg } = item as { loc?: unknown[]; msg?: string };
          const field = Array.isArray(loc) ? String(loc[loc.length - 1] ?? "") : "";
          if (msg) return field && field !== "body" ? `${field}: ${msg}` : msg;
        }
        return "";
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  return fallback;
}
