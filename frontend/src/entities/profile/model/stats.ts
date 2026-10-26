import type { AttemptSummary, SpeakingSubmissionSummary, WritingSubmissionSummary } from "@/shared/api";
import { resultHref, routes } from "@/shared/config";
import { bandBadgeClass, formatDate, roundHalf } from "@/shared/lib";

function scoreTone(score: number, total: number): string {
  const pct = total > 0 ? (score / total) * 100 : 0;
  if (pct >= 70) return "bg-emerald-50 text-emerald-700";
  if (pct >= 40) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

export type RecentItem = {
  id: string;
  title: string;
  meta: string;
  href: string;
  badge: string;
  badgeClass: string;
  createdAt: string | null;
};

type Sources = {
  attempts: AttemptSummary[];
  writing: WritingSubmissionSummary[];
  speaking: SpeakingSubmissionSummary[];
};

/** The six most recent graded items across every skill. */
export function buildRecentItems({ attempts, writing, speaking }: Sources): RecentItem[] {
  const readingListening = attempts.map((a) => ({
    id: `attempt-${a.id}`,
    title: a.test_title,
    meta: `${a.test_type} - ${formatDate(a.created_at)}`,
    href: resultHref(a.test_type, a.id),
    badge: `${a.score}/${a.total}`,
    badgeClass: scoreTone(a.score, a.total),
    createdAt: a.created_at,
  }));

  const writingItems = writing.map((w) => ({
    id: `writing-${w.id}`,
    title: w.task_title,
    meta: `${w.word_count} words - ${formatDate(w.created_at)}`,
    href: routes.writing.result(w.id),
    badge: w.band === null ? w.status : `Band ${w.band.toFixed(1)}`,
    badgeClass: bandBadgeClass(w.band),
    createdAt: w.created_at,
  }));

  const speakingItems = speaking.map((s) => ({
    id: `speaking-${s.id}`,
    title: `Speaking Part ${s.task_part}`,
    meta: formatDate(s.created_at),
    href: routes.speaking.result(s.id),
    badge: s.band === null ? "submitted" : `Band ${s.band.toFixed(1)}`,
    badgeClass: bandBadgeClass(s.band),
    createdAt: s.created_at,
  }));

  return [...readingListening, ...writingItems, ...speakingItems]
    .sort((a, b) => {
      const at = a.createdAt ? new Date(a.createdAt).getTime() : 0;
      const bt = b.createdAt ? new Date(b.createdAt).getTime() : 0;
      return bt - at;
    })
    .slice(0, 6);
}

function averageBand(values: (number | null)[]): number | null {
  const graded = values.filter((b): b is number => b !== null);
  return graded.length === 0 ? null : roundHalf(graded.reduce((sum, band) => sum + band, 0) / graded.length);
}

/** Overall average/best band plus a per-skill average. */
export function summarizeBands({ attempts, writing, speaking }: Sources) {
  const all = [...attempts.map((a) => a.band), ...writing.map((w) => w.band), ...speaking.map((s) => s.band)];
  const graded = all.filter((b): b is number => b !== null);
  return {
    avgBand: averageBand(all),
    bestBand: graded.length === 0 ? null : Math.max(...graded),
    skillBands: {
      reading: averageBand(attempts.filter((a) => a.test_type === "reading").map((a) => a.band)),
      listening: averageBand(attempts.filter((a) => a.test_type === "listening").map((a) => a.band)),
      writing: averageBand(writing.map((w) => w.band)),
      speaking: averageBand(speaking.map((s) => s.band)),
    },
  };
}

export type ActivityCell = { key: string; count: number; future: boolean };

export type ActivitySummary = {
  weeks: ActivityCell[][];
  total: number;
  activeDays: number;
  maxStreak: number;
  currentStreak: number;
  windowWeeks: number;
};

const dateKey = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** One year of per-day session counts laid out as week columns (Sunday first). */
export function buildActivity({ attempts, writing, speaking }: Sources, now: Date = new Date()): ActivitySummary {
  const counts = new Map<string, number>();
  const bump = (iso: string | null) => {
    if (!iso) return;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return;
    const key = dateKey(d);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  };
  attempts.forEach((a) => bump(a.created_at));
  writing.forEach((w) => bump(w.created_at));
  speaking.forEach((s) => bump(s.created_at));

  const WEEKS = 52;
  const today = new Date(now);
  today.setHours(0, 0, 0, 0);
  const start = new Date(today);
  start.setDate(start.getDate() - (WEEKS * 7 - 1));
  start.setDate(start.getDate() - start.getDay()); // rewind to Sunday for aligned columns

  const weeks: ActivityCell[][] = [];
  let week: ActivityCell[] = [];
  let total = 0;
  const cursor = new Date(start);
  for (let guard = 0; guard < 400; guard += 1) {
    const cur = new Date(cursor);
    const future = cur > today;
    const count = future ? 0 : counts.get(dateKey(cur)) ?? 0;
    if (!future) total += count;
    week.push({ key: dateKey(cur), count, future });
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
    const isSaturday = cur.getDay() === 6;
    cursor.setDate(cursor.getDate() + 1);
    if (isSaturday && cur >= today) break;
  }

  const flat = weeks.flat().filter((c) => !c.future);
  let activeDays = 0;
  let maxStreak = 0;
  let run = 0;
  flat.forEach((c) => {
    if (c.count > 0) {
      activeDays += 1;
      run += 1;
      maxStreak = Math.max(maxStreak, run);
    } else {
      run = 0;
    }
  });
  let currentStreak = 0;
  for (let i = flat.length - 1; i >= 0; i -= 1) {
    if (flat[i].count > 0) currentStreak += 1;
    else break;
  }

  return { weeks, total, activeDays, maxStreak, currentStreak, windowWeeks: weeks.length };
}
