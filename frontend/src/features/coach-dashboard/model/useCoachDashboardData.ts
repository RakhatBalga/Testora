"use client";

import { useEffect, useState } from "react";
import {
  api,
  type BandGapResult,
  type BandTrajectoryResult,
  type Blocker,
  type DailyPlanTask,
  type Streak,
  type Weakness,
  type WeeklyWeakest,
} from "@/shared/api";
import { type ProgressMovement } from "@/entities/coach";
import { IELTS_TARGET_BAND } from "@/shared/config";

export function useCoachDashboardData() {
  const [bandGap, setBandGap] = useState<BandGapResult | null>(null);
  const [blockers, setBlockers] = useState<Blocker[] | null>(null);
  const [weaknesses, setWeaknesses] = useState<Weakness[] | null>(null);
  const [trajectory, setTrajectory] = useState<BandTrajectoryResult | null>(null);
  const [recentMovement, setRecentMovement] = useState<ProgressMovement[] | null>(null);
  const [todaysPlan, setTodaysPlan] = useState<DailyPlanTask[] | null>(null);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [weeklyWeakest, setWeeklyWeakest] = useState<WeeklyWeakest | null>(null);

  useEffect(() => {
    let active = true;

    const settle = <T,>(promise: Promise<T>, apply: (value: T) => void, fallback: T) => {
      promise.then((value) => active && apply(value)).catch(() => active && apply(fallback));
    };

    settle(
      api.getBandGap(),
      setBandGap,
      {
        current: null,
        target: IELTS_TARGET_BAND,
        gap: null,
        per_skill: {},
        lowest_skill: null,
        has_data: false,
      }
    );
    settle(api.getBlockers(), (b) => setBlockers(b.blockers), { blockers: [] });
    settle(api.getWeaknesses(3), (w) => setWeaknesses(w.weaknesses), { weaknesses: [] });
    settle(api.getBandTrajectory(), setTrajectory, { points: [], delta: null, has_data: false });
    settle(
      api.getDailyPlan(undefined, 3),
      (plan) => setTodaysPlan(plan.plan),
      { generated_for: "", has_data: false, plan: [] }
    );
    settle(api.getStreak(), setStreak, { current_streak: 0, active_today: false });
    settle(api.getWeeklyWeakest(), setWeeklyWeakest, { has_data: false, skill: null, band: null, attempts: 0, days: 7 });

    (async () => {
      try {
        const submissions = await api.listWritingSubmissions();
        const latest = submissions.find((submission) => submission.status === "graded" && submission.band != null);
        if (!latest) {
          if (active) setRecentMovement([]);
          return;
        }

        const impact = await api.getProgressImpact("writing", latest.id);
        if (!active) return;
        if (!impact.has_previous || !impact.criteria) {
          setRecentMovement([]);
          return;
        }

        setRecentMovement(
          impact.criteria.slice(0, 4).map((criterion) => ({
            label: `Writing - ${criterion.name}`,
            from: criterion.from,
            to: criterion.to,
            direction: criterion.direction,
          }))
        );
      } catch {
        if (active) setRecentMovement([]);
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  const loading = bandGap === null;
  const hasData = !!bandGap?.has_data;
  const current = bandGap?.current ?? null;
  const target = bandGap?.target ?? IELTS_TARGET_BAND;
  const gapValue = bandGap?.gap ?? null;
  const mainBlocker = blockers?.[0] ?? null;
  const topWeaknesses = weaknesses?.slice(0, 3) ?? [];
  const nextTask = todaysPlan?.[0] ?? null;
  const primaryActionHref = mainBlocker?.fix_href ?? nextTask?.href ?? "/practice";

  return {
    loading,
    hasData,
    current,
    target,
    gapValue,
    mainBlocker,
    topWeaknesses,
    trajectory,
    recentMovement,
    todaysPlan,
    streak,
    weeklyWeakest,
    primaryActionHref,
  };
}
