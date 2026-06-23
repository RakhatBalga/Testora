/**
 * AI Coach dashboard data layer (Phase 1).
 *
 * Types and mock data for the coach dashboard spine. Kept separate from UI and
 * from the existing lib/dashboard.ts. Every export mirrors a future backend
 * shape, so when real analytics land these become API responses with no UI change.
 *
 * Future backend integration points are marked with `// BACKEND:` comments.
 */

export type CoachSkill = "listening" | "reading" | "writing" | "speaking";

/** Estimated band, per skill + overall, with a confidence signal. */
export interface BandEstimate {
  overall: number;
  target: number;
  perSkill: Record<CoachSkill, number>;
  /** how trustworthy the estimate is, driven by how much data exists */
  confidence: "low" | "medium" | "high";
  attempts: number;
}

/** Current vs target band and the deadline. */
export interface BandGap {
  current: number;
  target: number;
  /** target - current, always >= 0 */
  gap: number;
  /** ISO date string of the exam, or null if not set */
  examDate: string | null;
}

/** A single thing holding the user below their target band. */
export interface Blocker {
  id: string;
  /** display skill, e.g. "Writing" */
  skill: string;
  /** IELTS criterion, e.g. "Grammar Range & Accuracy" */
  criterion: string;
  explanation: string;
  /** the band this blocker is currently capping the user at */
  bandCap: number;
  /** where "Fix this" navigates (future-proofed) */
  fixHref: string;
}

/** One recommended task for today. */
export interface StudyTask {
  id: string;
  title: string;
  detail?: string;
  skill?: CoachSkill;
  estimatedMinutes?: number;
  /** where the task navigates (future-proofed) */
  href: string;
}

/** A measured change in one criterion/skill between attempts. */
export interface ProgressMovement {
  label: string;
  from: number | null;
  to: number | null;
  direction: "up" | "down" | "none";
}

/** One point on the band-over-time trajectory. */
export interface BandTrajectoryPoint {
  label: string;
  band: number;
}

/** Everything the coach dashboard needs in one object. */
export interface CoachDashboard {
  estimate: BandEstimate;
  gap: BandGap;
  mainBlocker: Blocker;
  blockers: Blocker[];
  todaysPlan: StudyTask[];
  recentMovement: ProgressMovement[];
  trajectory: BandTrajectoryPoint[];
  streakDays: number;
}

/* ------------------------------------------------------------------------ */
/* Helpers                                                                   */
/* ------------------------------------------------------------------------ */

/** Whole days from now until an ISO date (negative if past). */
export function daysUntil(isoDate: string | null, now = new Date()): number | null {
  if (!isoDate) return null;
  const exam = new Date(isoDate);
  const ms = exam.getTime() - now.getTime();
  return Math.ceil(ms / (1000 * 60 * 60 * 24));
}

export function greeting(d = new Date()): string {
  const h = d.getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/* ------------------------------------------------------------------------ */
/* Mock data — swap for `GET /coach/dashboard` later                         */
/* ------------------------------------------------------------------------ */

// BACKEND: examDate comes from goals.exam_date. Fixed here so the countdown
// stays meaningful in the demo (~34 days out from the project's "today").
const MOCK_EXAM_DATE = "2026-07-27";

export const coachDashboard: CoachDashboard = {
  // BACKEND: GET /analytics/band-estimate
  estimate: {
    overall: 6.0,
    target: 7.5,
    perSkill: { listening: 6.5, reading: 6.5, writing: 5.5, speaking: 5.5 },
    confidence: "medium",
    attempts: 5,
  },

  // BACKEND: derived from goals + latest band estimate
  gap: {
    current: 6.0,
    target: 7.5,
    gap: 1.5,
    examDate: MOCK_EXAM_DATE,
  },

  // BACKEND: GET /analytics/band-gap -> binding skill + criterion
  mainBlocker: {
    id: "writing-grammar",
    skill: "Writing",
    criterion: "Grammar Range & Accuracy",
    explanation:
      "This criterion has stayed at Band 6.0 across your last attempts — frequent article and complex-sentence errors.",
    bandCap: 6.0,
    fixHref: "/practice/writing",
  },

  // BACKEND: ranked from mistake memory aggregates
  blockers: [
    {
      id: "writing-grammar",
      skill: "Writing",
      criterion: "Grammar Range & Accuracy",
      explanation: "Frequent article and sentence-structure mistakes; little use of complex forms.",
      bandCap: 6.0,
      fixHref: "/practice/writing",
    },
    {
      id: "writing-task-response",
      skill: "Writing",
      criterion: "Task Response",
      explanation: "Prompts aren't fully addressed — some parts of the question go unanswered.",
      bandCap: 6.5,
      fixHref: "/practice/writing",
    },
    {
      id: "speaking-fluency",
      skill: "Speaking",
      criterion: "Fluency & Coherence",
      explanation: "Part 2 answers are too short (~45s) with frequent pauses; aim for the full ~2 min.",
      bandCap: 6.5,
      fixHref: "/practice/speaking",
    },
  ],

  // BACKEND: GET /quests/today (generated from blockers + plan)
  todaysPlan: [
    {
      id: "t1",
      title: "Complete a Writing Task 2 essay",
      detail: "Focus on addressing every part of the prompt",
      skill: "writing",
      estimatedMinutes: 40,
      href: "/practice/writing",
    },
    {
      id: "t2",
      title: "Practice Speaking Part 2",
      detail: "Record a full 2-minute long turn",
      skill: "speaking",
      estimatedMinutes: 15,
      href: "/practice/speaking",
    },
    {
      id: "t3",
      title: "Review your grammar mistakes",
      detail: "Articles & complex sentences from recent essays",
      skill: "writing",
      estimatedMinutes: 10,
      href: "/analytics",
    },
  ],

  // BACKEND: diff of band_estimates time series between recent attempts
  recentMovement: [
    { label: "Writing — Coherence", from: 6.0, to: 6.5, direction: "up" },
    { label: "Speaking — Fluency", from: 5.5, to: 6.0, direction: "up" },
    { label: "Writing — Grammar", from: 6.0, to: 6.0, direction: "none" },
    { label: "Lexical Resource", from: null, to: null, direction: "none" },
  ],

  // BACKEND: band_estimates ordered by created_at
  trajectory: [
    { label: "Wk 1", band: 5.0 },
    { label: "Wk 2", band: 5.5 },
    { label: "Wk 3", band: 5.5 },
    { label: "Wk 4", band: 5.5 },
    { label: "Wk 5", band: 6.0 },
    { label: "Wk 6", band: 6.0 },
  ],

  // BACKEND: streaks.current_streak
  streakDays: 17,
};
