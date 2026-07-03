import { useCallback, useEffect, useRef, useState } from "react";

type Persisted = {
  /** epoch ms when time runs out; null while paused */
  deadline: number | null;
  /** seconds remaining while paused; null while running */
  pausedRemaining: number | null;
};

function load(key: string): Persisted | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as Persisted) : null;
  } catch {
    return null;
  }
}

/**
 * A countdown that survives refresh by persisting an absolute deadline (so a
 * reload never grants extra time) and a separate paused-remaining value.
 *
 *  - `onExpire` fires exactly once when the clock reaches zero.
 *  - Pausing stores the remaining seconds; resuming rebuilds the deadline.
 */
export function useReadingTimer(
  storageKey: string,
  durationSeconds: number,
  onExpire: () => void
) {
  const key = `${storageKey}-timer`;
  const [remaining, setRemaining] = useState<number | null>(null);
  const [paused, setPaused] = useState(false);
  const expiredRef = useRef(false);
  const onExpireRef = useRef(onExpire);

  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);

  const persist = useCallback(
    (state: Persisted) => {
      try {
        localStorage.setItem(key, JSON.stringify(state));
      } catch {
        /* storage full / disabled — timer still works in-memory */
      }
    },
    [key]
  );

  // Initialise from storage or start fresh. A deadline that already expired
  // while the page was closed is treated as a stale session and restarted —
  // firing onExpire on mount would auto-submit an empty attempt the moment
  // the user re-opens the test (a phantom 0-score result). Expiry only
  // counts when the clock ticks down to zero during a live session.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const saved = load(key);
      const now = Date.now();
      const fresh = () => {
        persist({ deadline: now + durationSeconds * 1000, pausedRemaining: null });
        setRemaining(durationSeconds);
      };
      if (saved?.pausedRemaining != null && saved.pausedRemaining > 0) {
        setRemaining(saved.pausedRemaining);
        setPaused(true);
      } else if (saved?.deadline != null) {
        const left = Math.round((saved.deadline - now) / 1000);
        if (left > 0) setRemaining(left);
        else fresh();
      } else {
        fresh();
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [durationSeconds, key, persist]);

  // Tick once per second while running.
  useEffect(() => {
    if (remaining === null || paused) return;
    if (remaining <= 0) {
      if (!expiredRef.current) {
        expiredRef.current = true;
        onExpireRef.current();
      }
      return;
    }
    const t = setTimeout(() => setRemaining((r) => (r === null ? r : r - 1)), 1000);
    return () => clearTimeout(t);
  }, [remaining, paused]);

  const pause = useCallback(() => {
    if (remaining === null) return;
    setPaused(true);
    persist({ deadline: null, pausedRemaining: remaining });
  }, [remaining, persist]);

  const resume = useCallback(() => {
    if (remaining === null) return;
    setPaused(false);
    persist({ deadline: Date.now() + remaining * 1000, pausedRemaining: null });
  }, [remaining, persist]);

  const clear = useCallback(() => {
    try {
      localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  }, [key]);

  return { remaining, paused, pause, resume, clear };
}
