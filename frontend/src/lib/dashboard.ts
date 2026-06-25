export const SKILLS = ["listening", "reading", "writing", "speaking"] as const;
export type Skill = (typeof SKILLS)[number];

export type SkillTone = "sky" | "violet" | "emerald" | "amber";

export const skillMeta: Record<
  Skill,
  {
    label: string;
    tone: SkillTone;
    href: string;
    blurb: string;
  }
> = {
  listening: {
    label: "Listening",
    tone: "sky",
    href: "/tests/listening",
    blurb: "Audio recordings with section-by-section question sets.",
  },
  reading: {
    label: "Reading",
    tone: "violet",
    href: "/tests/reading",
    blurb: "Academic passages with mixed IELTS question types.",
  },
  writing: {
    label: "Writing",
    tone: "emerald",
    href: "/writing",
    blurb: "Task 1 & Task 2 responses with instant band feedback.",
  },
  speaking: {
    label: "Speaking",
    tone: "amber",
    href: "/speaking",
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

export function greeting(d = new Date()): string {
  const h = d.getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}
