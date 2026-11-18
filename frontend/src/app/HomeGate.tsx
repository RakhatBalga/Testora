"use client";

import { useLayoutEffect, type ReactNode } from "react";
import { SESSION_HINT_CLASS } from "@/shared/api";
import { useAuth } from "@/shared/auth";
import { CoachDashboard } from "@/widgets/coach-dashboard";

/**
 * `/` shows the dashboard to signed-in users and the public landing to
 * everyone else. The landing is passed in as server-rendered markup so the
 * prerendered HTML (crawlers, link previews, view-source) contains real
 * content; auth is only known in the browser, where a token swaps it out.
 *
 * The markup is the same on the server and during hydration. For a tab that
 * already holds a token, the head script in the root layout sets a class on
 * <html> and CSS hides the landing until the dashboard replaces it, so
 * signed-in users do not see the landing flash first.
 */
export function HomeGate({ landing }: { landing: ReactNode }) {
  const { token, username, ready } = useAuth();

  // No session after all (signed out, or the token is gone): show the landing.
  useLayoutEffect(() => {
    if (ready && !token) document.documentElement.classList.remove(SESSION_HINT_CLASS);
  }, [ready, token]);

  if (ready && token) return <CoachDashboard username={username} />;
  return (
    <div data-public-landing className="contents">
      {landing}
    </div>
  );
}
