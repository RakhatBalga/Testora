"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { remainingSeconds, resolveTimerStart, type PersistedTimer } from "./examTimer";

function load(key: string): PersistedTimer | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as PersistedTimer) : null;
  } catch {
    return null;
  }
}

type Options = {
  /**
   * Called when a stored deadline already passed while the page was closed.
   * Return true if there is saved work worth submitting (the timer then
   * expires immediately); otherwise the timer restarts so re-opening a test
   * never submits a phantom empty attempt.
   */
  shouldSubmitStale?: () => boolean;
};

/**
 * A countdown driven by an absolute deadline persisted in localStorage.
 * Every tick recomputes the remaining time from the clock (not by
 * decrementing), and it re-syncs on visibilitychange/focus, so background-tab
 * throttling or a suspended mobile browser can neither stretch nor lose time.
 *
 *  - Pass `durationSeconds = null` until the real duration is known (or while
 *    reviewing a finished attempt); the timer does not start until then.
 *  - `onExpire` fires exactly once when the clock reaches zero.
 */
export function useExamTimer(
  storageKey: string,
  durationSeconds: number | null,
  onExpire: () => void,
  options: Options = {},
) {
  const key = `${storageKey}-timer`;
  const [remaining, setRemaining] = useState<number | null>(null);
  const [paused, setPaused] = useState(false);
  const deadlineRef = useRef<number | null>(null);
  const expiredRef = useRef(false);
  const onExpireRef = useRef(onExpire);
  const staleRef = useRef(options.shouldSubmitStale);

  useEffect(() => {
    onExpireRef.current = onExpire;
    staleRef.current = options.shouldSubmitStale;
  });

  const persist = useCallback(
    (state: PersistedTimer) => {
      try {
        localStorage.setItem(key, JSON.stringify(state));
      } catch {
        /* storage full / disabled — timer still works in-memory */
      }
    },
    [key],
  );

  // Initialise from storage, or start fresh once the duration is known.
  useEffect(() => {
    if (durationSeconds === null) return;
    const timer = window.setTimeout(() => {
      const now = Date.now();
      let start = resolveTimerStart(load(key), now, durationSeconds);
      if (start.kind === "expired" && !staleRef.current?.()) start = { kind: "fresh" };
      if (start.kind === "fresh") {
        deadlineRef.current = now + durationSeconds * 1000;
        persist({ deadline: deadlineRef.current, pausedRemaining: null });
        setRemaining(durationSeconds);
      } else if (start.kind === "running") {
        deadlineRef.current = start.deadline;
        setRemaining(remainingSeconds(start.deadline, now));
      } else if (start.kind === "paused") {
        deadlineRef.current = null;
        setRemaining(start.remaining);
        setPaused(true);
      } else {
        deadlineRef.current = now;
        setRemaining(0);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [durationSeconds, key, persist]);

  const started = remaining !== null && durationSeconds !== null;

  // Tick: recompute from the deadline, and re-sync as soon as the tab is back.
  useEffect(() => {
    if (!started || paused) return;
    const sync = () => {
      const deadline = deadlineRef.current;
      if (deadline === null) return;
      const left = remainingSeconds(deadline, Date.now());
      setRemaining(left);
      if (left <= 0 && !expiredRef.current) {
        expiredRef.current = true;
        onExpireRef.current();
      }
    };
    sync();
    const id = window.setInterval(sync, 1000);
    document.addEventListener("visibilitychange", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", sync);
      window.removeEventListener("focus", sync);
    };
  }, [started, paused]);

  const pause = useCallback(() => {
    const deadline = deadlineRef.current;
    if (deadline === null) return;
    const left = remainingSeconds(deadline, Date.now());
    deadlineRef.current = null;
    setRemaining(left);
    setPaused(true);
    persist({ deadline: null, pausedRemaining: left });
  }, [persist]);

  const resume = useCallback(() => {
    if (remaining === null) return;
    deadlineRef.current = Date.now() + remaining * 1000;
    persist({ deadline: deadlineRef.current, pausedRemaining: null });
    setPaused(false);
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
