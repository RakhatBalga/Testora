const FLOW_KEY = "testora.google.flow";
const MAX_AGE_MS = 10 * 60 * 1000;

export function beginGoogleFlow(storage: Storage = sessionStorage): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  const state = btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
  storage.setItem(FLOW_KEY, JSON.stringify({ state, createdAt: Date.now() }));
  return state;
}

export function consumeGoogleFlow(state: string | null, storage: Storage = sessionStorage): string {
  const raw = storage.getItem(FLOW_KEY);
  storage.removeItem(FLOW_KEY);
  try {
    const saved = JSON.parse(raw ?? "null");
    const age = Date.now() - saved?.createdAt;
    if (state && saved?.state === state && Number.isFinite(age) && age >= 0 && age < MAX_AGE_MS) {
      return state;
    }
  } catch { /* Treat invalid storage as an absent flow. */ }
  throw new Error("Google sign-in expired or did not start in this tab. Please try again.");
}
