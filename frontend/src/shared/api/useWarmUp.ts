"use client";

import { useEffect } from "react";
import { warmUpServer } from "./http";

/** Pings the backend once on mount so a sleeping host wakes while the user reads/types. */
export function useWarmUp(): void {
  useEffect(() => {
    warmUpServer();
  }, []);
}
