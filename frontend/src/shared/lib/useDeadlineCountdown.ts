"use client";

import { useEffect, useRef, useState } from "react";
import { remainingSeconds } from "./examTimer";

/**
 * Short in-memory countdown (Speaking prep/answer time). Starts a fresh
 * `seconds` countdown every time `running` becomes true and derives the value
 * from a deadline, so a throttled background tab cannot stretch it.
 */
export function useDeadlineCountdown(running: boolean, seconds: number, onDone: () => void): number {
  const [left, setLeft] = useState(seconds);
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    onDoneRef.current = onDone;
  });

  useEffect(() => {
    if (!running) return;
    const deadline = Date.now() + seconds * 1000;
    let finished = false;
    const sync = () => {
      const remaining = remainingSeconds(deadline, Date.now());
      setLeft(remaining);
      if (remaining <= 0 && !finished) {
        finished = true;
        onDoneRef.current();
      }
    };
    sync(); // show the real value immediately, never a 00:00 flash
    const id = window.setInterval(sync, 250);
    document.addEventListener("visibilitychange", sync);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", sync);
    };
  }, [running, seconds]);

  return running ? left : seconds;
}
