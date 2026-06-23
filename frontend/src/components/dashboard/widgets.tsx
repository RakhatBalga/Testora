import { type ReactNode } from "react";
import { Headphones, BookOpen, PenLine, Mic, type LucideIcon } from "lucide-react";
import { type Skill, toneClasses, skillMeta } from "@/lib/dashboard";

export const skillIcons: Record<Skill, LucideIcon> = {
  listening: Headphones,
  reading: BookOpen,
  writing: PenLine,
  speaking: Mic,
};

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-[1.75rem]">
          {title}
        </h1>
        {subtitle && <p className="mt-1 text-[var(--text-secondary)]">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function ProgressBar({
  value,
  className = "",
  barClass = "bg-[var(--brand)]",
}: {
  value: number;
  className?: string;
  barClass?: string;
}) {
  return (
    <div className={`h-2 overflow-hidden rounded-full bg-[var(--border)] ${className}`}>
      <div
        className={`h-full rounded-full transition-[width] duration-500 ease-out ${barClass}`}
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

export function StatTile({
  label,
  value,
  hint,
  icon,
  accent = "text-[var(--brand)]",
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: ReactNode;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-[var(--text-secondary)]">{label}</p>
        {icon && <span className={accent}>{icon}</span>}
      </div>
      <p className="mt-2 text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-[var(--text-secondary)]">{hint}</p>}
    </div>
  );
}

/** Circular progress ring (SVG). `value` is 0..1. */
export function Ring({
  value,
  size = 132,
  stroke = 12,
  children,
}: {
  value: number;
  size?: number;
  stroke?: number;
  children?: ReactNode;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - value);
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--brand)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  );
}

export function SkillRow({ skill }: { skill: Skill }) {
  const m = skillMeta[skill];
  const Icon = skillIcons[skill];
  const t = toneClasses[m.tone];
  return (
    <div className="flex items-center gap-3">
      <span className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${t.soft}`}>
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between text-sm">
          <span className="font-medium text-[var(--text-primary)]">{m.label}</span>
          <span className="font-semibold text-[var(--text-secondary)]">
            {Math.round(m.progress * 100)}%
          </span>
        </div>
        <ProgressBar value={m.progress} barClass={t.bar} />
      </div>
    </div>
  );
}
