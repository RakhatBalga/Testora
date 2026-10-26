"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/shared/auth";
import { CoachDashboard } from "@/widgets/coach-dashboard";

/**
 * `/` shows the dashboard to signed-in users and the public landing to
 * everyone else. The landing is passed in as server-rendered markup so the
 * prerendered HTML (crawlers, link previews, view-source) contains real
 * content; auth is only known in the browser, where a token swaps it out.
 */
export function HomeGate({ landing }: { landing: ReactNode }) {
  const { token, username, ready } = useAuth();
  if (ready && token) return <CoachDashboard username={username} />;
  return <>{landing}</>;
}
