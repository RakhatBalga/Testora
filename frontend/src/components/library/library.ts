import type { AttemptSummary, Test } from "@/lib/api";

export type TestStatus = "completed" | "in_progress" | "not_started";

/** Per-skill accent, drawn from the existing Tailwind palette (reading = violet,
 *  listening = sky). Used sparingly — eyebrow, badges, progress, CTA tint. */
export type Accent = {
  text: string;
  softBg: string;
  bar: string;
  glow: string;
  ring: string;
};

export const ACCENTS: Record<string, Accent> = {
  reading: {
    text: "text-violet-600",
    softBg: "bg-violet-50",
    bar: "bg-violet-500",
    glow: "shadow-violet-500/10",
    ring: "ring-violet-500/15",
  },
  listening: {
    text: "text-sky-600",
    softBg: "bg-sky-50",
    bar: "bg-sky-500",
    glow: "shadow-sky-500/10",
    ring: "ring-sky-500/15",
  },
};

export function accentFor(type: string): Accent {
  return ACCENTS[type] ?? ACCENTS.reading;
}

/** localStorage key prefix used by the exam pages (reading-/listening-). */
function storeKey(type: string, id: number): string {
  return `${type}-${id}`;
}

/** Count answered questions saved for an in-progress attempt. */
function answeredFromStorage(type: string, id: number): number {
  try {
    const raw = localStorage.getItem(`${storeKey(type, id)}-answers`);
    if (!raw) return 0;
    const map = JSON.parse(raw) as Record<string, unknown>;
    return Object.values(map).filter((v) =>
      Array.isArray(v) ? v.length > 0 : typeof v === "string" && v.trim() !== ""
    ).length;
  } catch {
    return 0;
  }
}

export type TestProgress = {
  status: TestStatus;
  /** 0..1 — answered ratio for in-progress; 1 for completed */
  ratio: number;
  answered: number;
  /** epoch ms of last local activity, if known */
  updatedAt: number | null;
  /** best band from a completed attempt, if any */
  band: number | null;
};

/**
 * Derive a test's status from completed attempts (server) + locally-saved
 * in-progress answers (localStorage). Completed wins over in-progress.
 */
export function deriveProgress(
  test: Test,
  attempts: AttemptSummary[]
): TestProgress {
  const mine = attempts.filter((a) => a.test_id === test.id);
  const total = test.question_count ?? 0;

  if (mine.length > 0) {
    const band = mine
      .map((a) => a.band)
      .filter((b): b is number => b !== null)
      .reduce((max, b) => Math.max(max, b), Number.NEGATIVE_INFINITY);
    return {
      status: "completed",
      ratio: 1,
      answered: total,
      updatedAt: new Date(mine[0].created_at).getTime(),
      band: Number.isFinite(band) ? band : null,
    };
  }

  const answered = answeredFromStorage(test.test_type, test.id);
  if (answered > 0) {
    let updatedAt: number | null = null;
    const u = localStorage.getItem(`${storeKey(test.test_type, test.id)}-updated`);
    if (u) updatedAt = Number(u) || null;
    return {
      status: "in_progress",
      ratio: total > 0 ? Math.min(1, answered / total) : 0,
      answered,
      updatedAt,
      band: null,
    };
  }

  return { status: "not_started", ratio: 0, answered: 0, updatedAt: null, band: null };
}

export function relativeTime(iso: string | number): string {
  const then = typeof iso === "number" ? iso : new Date(iso).getTime();
  const diff = Date.now() - then;
  const min = Math.round(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} ${hr === 1 ? "hour" : "hours"} ago`;
  const day = Math.round(hr / 24);
  if (day === 1) return "yesterday";
  if (day < 7) return `${day} days ago`;
  return new Date(then).toLocaleDateString();
}

export function roundHalf(n: number): number {
  return Math.round(n * 2) / 2;
}
