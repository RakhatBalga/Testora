"use client";

import { useAuth } from "@/shared/auth";
import { CoachDashboard } from "@/widgets/coach-dashboard";
import { PublicLanding } from "@/widgets/landing";

export default function HomeRoute() {
  const { token, username, ready } = useAuth();
  if (!ready) return null;
  return token ? <CoachDashboard username={username} /> : <PublicLanding />;
}
