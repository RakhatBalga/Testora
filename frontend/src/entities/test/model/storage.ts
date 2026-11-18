/**
 * localStorage prefix for an in-progress exam. Scoped by username so two people
 * sharing a browser never see each other's answers or "in progress" badges.
 */
export function examStorageKey(type: string, username: string | null | undefined, id: number): string {
  return `${type}-${username ?? "anonymous"}-${id}`;
}

/**
 * Idempotency key for the attempt stored under `storeKey`. Created once and kept
 * next to the draft, so a retry after a timeout or a reload sends the same key
 * and the server returns the first attempt instead of saving a second one.
 */
export function examSubmissionKey(storeKey: string): string {
  const slot = `${storeKey}-submission-key`;
  const existing = localStorage.getItem(slot);
  if (existing) return existing;
  const created = crypto.randomUUID();
  localStorage.setItem(slot, created);
  return created;
}

/** Forget the key once the attempt is saved or a new attempt starts. */
export function clearExamSubmissionKey(storeKey: string): void {
  localStorage.removeItem(`${storeKey}-submission-key`);
}

/**
 * True when the URL carries `?retake=1`. The flag is removed from the address
 * bar in the same step, so reloading the page later cannot start another retake.
 */
export function consumeRetakeFlag(): boolean {
  const url = new URL(window.location.href);
  if (url.searchParams.get("retake") !== "1") return false;
  url.searchParams.delete("retake");
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  return true;
}
