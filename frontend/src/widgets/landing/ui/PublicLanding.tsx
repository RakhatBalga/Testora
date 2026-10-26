"use client";

import { useWarmUp } from "@/shared/api";
import Landing from "./Landing";

export function PublicLanding() {
  // Wake the free-tier backend while the visitor reads the page.
  useWarmUp();
  return <Landing />;
}
