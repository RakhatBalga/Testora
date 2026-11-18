type StoredKey = { key: string; text: string };

const slot = (draftKey: string) => `${draftKey}-submission-key`;

/**
 * Idempotency key for submitting `text` from the draft stored under `draftKey`.
 * The key is bound to the exact text it was first sent with: a retry or a reload
 * with the same text reuses it, so the server returns the submission it already
 * has; an edited essay gets a new key, so the changes are never dropped in
 * favour of the earlier submission.
 */
export function writingSubmissionKey(draftKey: string, text: string): string {
  try {
    const stored = JSON.parse(localStorage.getItem(slot(draftKey)) ?? "null") as StoredKey | null;
    if (stored && typeof stored.key === "string" && stored.text === text) return stored.key;
  } catch {
    /* corrupt entry: replace it */
  }
  const key = crypto.randomUUID();
  localStorage.setItem(slot(draftKey), JSON.stringify({ key, text } satisfies StoredKey));
  return key;
}

/** Forget the key once the submission is accepted or the draft is discarded. */
export function clearWritingSubmissionKey(draftKey: string): void {
  localStorage.removeItem(slot(draftKey));
}
