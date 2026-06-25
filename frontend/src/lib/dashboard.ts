/**
 * Mock IELTS learner data.
 *
 * This is a single, swappable source for the dashboard product surfaces
 * (Dashboard / Practice / Mock Tests / Analytics). When the backend grows the
 * matching entities (Profile, Goal, PracticeSession, MockTest, Analytics) these
 * exports become API calls with the same shapes — the UI does not need to change.
 */

export const SKILLS = ["listening", "reading", "writing", "speaking"] as const;
export type Skill = (typeof SKILLS)[number];

export type SkillTone = "sky" | "violet" | "emerald" | "amber";

export const skillMeta: Record<
  Skill,
  {
    label: string;
    tone: SkillTone;
    /** route to the real practice experience */
    href: string;
    progress: number; // 0..1
    exercises: number;
    avgBand: number;
    blurb: string;
  }
> = {
  listening: {
    label: "Listening",
    tone: "sky",
    href: "/tests/listening",
    progress: 0.65,
    exercises: 24,
    avgBand: 6.5,
    blurb: "Audio recordings with section-by-section question sets.",
  },
  reading: {
    label: "Reading",
    tone: "violet",
    href: "/tests/reading",
    progress: 0.72,
    exercises: 18,
    avgBand: 7.0,
    blurb: "Academic passages with mixed IELTS question types.",
  },
  writing: {
    label: "Writing",
    tone: "emerald",
    href: "/writing",
    progress: 0.48,
    exercises: 12,
    avgBand: 6.0,
    blurb: "Task 1 & Task 2 responses with instant band feedback.",
  },
  speaking: {
    label: "Speaking",
    tone: "amber",
    href: "/speaking",
    progress: 0.41,
    exercises: 9,
    avgBand: 5.5,
    blurb: "Recorded answers across all three speaking parts.",
  },
};

export const toneClasses: Record<
  SkillTone,
  { soft: string; solid: string; text: string; bar: string }
> = {
  sky: {
    soft: "bg-sky-50 text-sky-600",
    solid: "bg-sky-500",
    text: "text-sky-600",
    bar: "bg-sky-500",
  },
  violet: {
    soft: "bg-violet-50 text-violet-600",
    solid: "bg-violet-500",
    text: "text-violet-600",
    bar: "bg-violet-500",
  },
  emerald: {
    soft: "bg-emerald-50 text-emerald-600",
    solid: "bg-emerald-500",
    text: "text-emerald-600",
    bar: "bg-emerald-500",
  },
  amber: {
    soft: "bg-amber-50 text-amber-600",
    solid: "bg-amber-500",
    text: "text-amber-600",
    bar: "bg-amber-500",
  },
};

export const learner = {
  targetBand: 7.5,
  currentBand: 6.0,
  weeklyGoalHours: 10,
  weeklyDoneHours: 6.5,
  streakDays: 17,
  completedExercises: 128,
  studyTimeHours: 47,
  accuracy: 0.74,
  completionRate: 0.62,
  /** how close to the target band, 0..1 — used in the hero card */
  overallProgress: 0.68,
};

/** Sub-sections shown on each /practice/[skill] detail page. */
export const practiceSections: Record<
  Skill,
  { group: string; items: { name: string; progress: number; count: number }[] }[]
> = {
  listening: [
    {
      group: "Sections",
      items: [
        { name: "Part 1 — Everyday conversation", progress: 0.8, count: 6 },
        { name: "Part 2 — Monologue", progress: 0.66, count: 6 },
        { name: "Part 3 — Academic discussion", progress: 0.5, count: 6 },
        { name: "Part 4 — Lecture", progress: 0.42, count: 6 },
      ],
    },
  ],
  reading: [
    {
      group: "Academic Reading",
      items: [
        { name: "Passage 1", progress: 0.85, count: 6 },
        { name: "Passage 2", progress: 0.7, count: 6 },
        { name: "Passage 3", progress: 0.55, count: 6 },
      ],
    },
  ],
  writing: [
    {
      group: "Tasks",
      items: [
        { name: "Task 1 — Report", progress: 0.55, count: 6 },
        { name: "Task 2 — Essay", progress: 0.42, count: 6 },
      ],
    },
  ],
  speaking: [
    {
      group: "Parts",
      items: [
        { name: "Part 1 — Interview", progress: 0.6, count: 4 },
        { name: "Part 2 — Long turn", progress: 0.38, count: 3 },
        { name: "Part 3 — Discussion", progress: 0.3, count: 2 },
      ],
    },
  ],
};

export type Activity = {
  skill: Skill;
  title: string;
  detail: string;
  when: string;
  band?: number;
};

export const recentActivity: Activity[] = [
  { skill: "reading", title: "Academic Reading · Passage 2", detail: "11 / 13 correct", when: "2h ago", band: 7.0 },
  { skill: "writing", title: "Writing Task 2 · Opinion essay", detail: "AI feedback ready", when: "Yesterday", band: 6.0 },
  { skill: "listening", title: "Listening · Part 3", detail: "8 / 10 correct", when: "Yesterday", band: 6.5 },
  { skill: "speaking", title: "Speaking · Part 2 long turn", detail: "Fluency improving", when: "2 days ago", band: 5.5 },
];

export type MockTest = {
  id: string;
  title: string;
  durationMin: number;
  expectedBand: number;
  sections: Skill[];
  status: "new" | "in-progress" | "completed";
};

export const mockTests: MockTest[] = [
  {
    id: "academic-01",
    title: "Full Academic Test 1",
    durationMin: 165,
    expectedBand: 6.5,
    sections: ["listening", "reading", "writing", "speaking"],
    status: "completed",
  },
  {
    id: "academic-02",
    title: "Full Academic Test 2",
    durationMin: 165,
    expectedBand: 7.0,
    sections: ["listening", "reading", "writing", "speaking"],
    status: "in-progress",
  },
  {
    id: "academic-03",
    title: "Full Academic Test 3",
    durationMin: 165,
    expectedBand: 7.5,
    sections: ["listening", "reading", "writing", "speaking"],
    status: "new",
  },
];

/** Band history for the Analytics line chart (oldest → newest). */
export const bandHistory: { label: string; band: number }[] = [
  { label: "Wk 1", band: 5.0 },
  { label: "Wk 2", band: 5.5 },
  { label: "Wk 3", band: 5.5 },
  { label: "Wk 4", band: 6.0 },
  { label: "Wk 5", band: 6.0 },
  { label: "Wk 6", band: 6.5 },
];

/** Per-skill weekly progress series for the Analytics bars (0..1). */
export const skillSeries: Record<Skill, number[]> = {
  listening: [0.4, 0.5, 0.55, 0.6, 0.62, 0.65],
  reading: [0.5, 0.55, 0.6, 0.66, 0.7, 0.72],
  writing: [0.3, 0.34, 0.38, 0.42, 0.45, 0.48],
  speaking: [0.25, 0.3, 0.33, 0.36, 0.39, 0.41],
};

export const leaderboard = {
  weeklyLearners: [
    { name: "Aigerim", hours: 14.5 },
    { name: "You", hours: 6.5 },
    { name: "Daniyar", hours: 5.0 },
  ],
  topImprovements: [
    { name: "Madina", delta: 1.5 },
    { name: "You", delta: 1.0 },
    { name: "Timur", delta: 0.5 },
  ],
  highestStreaks: [
    { name: "Aruzhan", days: 41 },
    { name: "You", days: 17 },
    { name: "Bekzat", days: 12 },
  ],
};

export function greeting(d = new Date()): string {
  const h = d.getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}
