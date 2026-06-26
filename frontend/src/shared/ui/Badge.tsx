import { ReactNode } from "react";

type Tone = "blue" | "violet" | "green" | "slate";

const tones: Record<Tone, string> = {
  blue: "bg-blue-50 text-blue-700 ring-blue-100",
  violet: "bg-violet-50 text-violet-700 ring-violet-100",
  green: "bg-green-50 text-green-700 ring-green-100",
  slate: "bg-slate-100 text-slate-600 ring-slate-200",
};

export function Badge({
  children,
  tone = "blue",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide ring-1 ring-inset ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
