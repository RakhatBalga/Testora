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
  onExpireRef.current = onExpire;

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

  // Initialise from storage or start fresh.
  useEffect(() => {
    const saved = load(key);
    const now = Date.now();
    if (saved?.pausedRemaining != null) {
      setRemaining(saved.pausedRemaining);
      setPaused(true);
    } else if (saved?.deadline != null) {
      setRemaining(Math.max(0, Math.round((saved.deadline - now) / 1000)));
    } else {
      const deadline = now + durationSeconds * 1000;
      persist({ deadline, pausedRemaining: null });
      setRemaining(durationSeconds);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

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
