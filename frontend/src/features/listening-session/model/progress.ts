import { getStoredUsername, type ListeningProgress } from "@/shared/api";

export type ProgressInput = Omit<ListeningProgress, "status" | "updated_at">;
type Draft = { progress: ProgressInput; updatedAt: number };

export function listeningSessionKey(id: number, version: string, mode = "practice") {
  return `listening-${encodeURIComponent(getStoredUsername() ?? "anonymous")}-${id}-${version}-${mode}`;
}

export function readDraft(key: string): Draft | null {
  try {
    const draft = JSON.parse(localStorage.getItem(`${key}-draft`) ?? "null");
    if (!draft || !Number.isFinite(draft.updatedAt) || !draft.progress ||
      typeof draft.progress.answers !== "object" || draft.progress.answers === null ||
      !Number.isInteger(draft.progress.current_section) || draft.progress.current_section < 0 ||
      draft.progress.current_section > 3 || !Number.isFinite(draft.progress.audio_position) ||
      !Number.isFinite(draft.progress.max_audio_position)) return null;
    return draft;
  } catch { return null; }
}

export function restoreProgress(key: string, saved: ListeningProgress | null): ListeningProgress | null {
  const draft = readDraft(key);
  // API timestamps are UTC, including responses without an explicit offset.
  const stamp = saved?.updated_at;
  const serverTime = stamp ? Date.parse(/[Zz]|[+-]\d\d:\d\d$/.test(stamp) ? stamp : `${stamp}Z`) : 0;
  if (draft && (saved?.status !== "submitted" || draft.updatedAt > serverTime)) {
    return { ...draft.progress, status: "in_progress", updated_at: new Date(draft.updatedAt).toISOString() };
  }
  return saved?.status === "in_progress" ? saved : null;
}

/** Keep a local recovery copy immediately; serialize network writes so older
 * snapshots cannot finish after newer ones or after submission. */
export function createProgressWriter(
  key: string,
  save: (progress: ProgressInput) => Promise<unknown>,
  report: (message: string) => void,
) {
  let pending: Draft | null = null;
  let running: Promise<void> | null = null;
  let stopped = false;
  function record(progress: ProgressInput) {
    if (stopped) return;
    pending = { progress, updatedAt: Date.now() };
    try { localStorage.setItem(`${key}-draft`, JSON.stringify(pending)); }
    catch { report("Browser storage is unavailable. Keep this page open until progress is saved."); }
  }
  function flush(): Promise<void> {
    if (running) return running;
    if (stopped || !pending) return Promise.resolve();
    running = (async () => {
      while (pending && !stopped) {
        const snapshot = pending;
        pending = null;
        try {
          await save(snapshot.progress);
          if (!pending && localStorage.getItem(`${key}-draft`) === JSON.stringify(snapshot)) {
            localStorage.removeItem(`${key}-draft`);
          }
          report("");
        } catch {
          pending ??= snapshot;
          report("Progress has not synced. Keep this page open; saving will retry automatically.");
          break;
        }
      }
    })().finally(() => { running = null; });
    return running;
  }
  return {
    record, flush,
    async stop() { stopped = true; await running; },
    resume() { stopped = false; },
    clear() {
      pending = null;
      try { localStorage.removeItem(`${key}-draft`); } catch { /* storage disabled */ }
    },
  };
}
