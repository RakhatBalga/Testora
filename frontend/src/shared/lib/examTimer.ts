/** Whole seconds left until `deadline` (epoch ms), never negative. */
export function remainingSeconds(deadline: number, now: number): number {
  return Math.max(0, Math.ceil((deadline - now) / 1000));
}

export type PersistedTimer = {
  /** epoch ms when time runs out; null while paused */
  deadline: number | null;
  /** seconds remaining while paused; null while running */
  pausedRemaining: number | null;
};

export type TimerStart =
  | { kind: "fresh" }
  | { kind: "running"; deadline: number }
  | { kind: "paused"; remaining: number }
  /** The stored deadline passed while the page was closed. */
  | { kind: "expired" };

/**
 * Decide how a timer starts given what was stored. Stored values are clamped to
 * the test's real duration, so a stale 60-minute deadline never outlives a
 * 20-minute test.
 */
export function resolveTimerStart(
  saved: PersistedTimer | null,
  now: number,
  durationSeconds: number,
): TimerStart {
  if (saved?.pausedRemaining != null && saved.pausedRemaining > 0) {
    return { kind: "paused", remaining: Math.min(saved.pausedRemaining, durationSeconds) };
  }
  if (saved?.deadline != null) {
    if (saved.deadline <= now) return { kind: "expired" };
    return { kind: "running", deadline: Math.min(saved.deadline, now + durationSeconds * 1000) };
  }
  return { kind: "fresh" };
}

/** Format seconds as mm:ss (e.g. 3605 -> "60:05"). */
export function formatClockSeconds(seconds: number | null): string {
  if (seconds === null) return "--:--";
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}
