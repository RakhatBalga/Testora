"use client";

import { ArrowRight, TrendingUp, TrendingDown, Minus, CheckCircle2, AlertCircle } from "lucide-react";
import { type ProgressImpact as ProgressImpactData, type ProgressMistakeItem } from "@/lib/api";

/**
 * Before → After payoff card for a graded submission. Pure presentation over
 * the /analytics/progress-impact diff: band move, per-criterion change, and
 * which mistake categories were resolved / reduced / appeared.
 */
export function ProgressImpact({ data }: { data: ProgressImpactData | null }) {
  if (!data || !data.supported || data.found === false) return null;

  // First graded attempt — nothing to compare against yet.
  if (!data.has_previous) {
    return (
      <section className="rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">Your progress</h2>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          This is your first graded attempt for this skill. Submit another and I&apos;ll show you
          exactly what improved.
        </p>
      </section>
    );
  }

  const delta = data.band_delta ?? 0;
  const up = delta > 0;
  const down = delta < 0;
  const prevBand = data.previous?.band;
  const curBand = data.current?.band;
  const m = data.mistakes;

  return (
    <section className="overflow-hidden rounded-3xl border border-[var(--border)] bg-white shadow-sm">
      {/* header: before -> after band move */}
      <div className="flex items-center justify-between gap-4 border-b border-[var(--border)] bg-slate-50/60 p-6">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">Since your last attempt</h2>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
            up ? "bg-emerald-50 text-emerald-600" : down ? "bg-red-50 text-red-600" : "bg-slate-100 text-slate-500"
          }`}
        >
          {up ? <TrendingUp className="h-3.5 w-3.5" /> : down ? <TrendingDown className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}
          {up ? "+" : ""}
          {delta.toFixed(1)} band
        </span>
      </div>

      <div className="space-y-6 p-6">
        {/* big before -> after */}
        <div className="flex items-center justify-center gap-5">
          <BandPill label="Previous" value={prevBand} muted />
          <ArrowRight className="h-5 w-5 flex-shrink-0 text-slate-300" />
          <BandPill label="Current" value={curBand} highlight={up} />
        </div>

        {/* per-criterion movement */}
        {data.criteria && data.criteria.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Criteria
            </h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {data.criteria.map((c) => {
                const tone =
                  c.direction === "up" ? "text-emerald-600" : c.direction === "down" ? "text-red-600" : "text-slate-400";
                const Icon = c.direction === "up" ? TrendingUp : c.direction === "down" ? TrendingDown : Minus;
                return (
                  <div
                    key={c.name}
                    className="flex items-center justify-between rounded-xl border border-[var(--border)] px-3.5 py-2.5"
                  >
                    <span className="text-sm font-medium text-[var(--text-primary)]">{c.name}</span>
                    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${tone}`}>
                      {c.from.toFixed(1)} <ArrowRight className="h-3 w-3 text-slate-300" /> {c.to.toFixed(1)}
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* mistake changes */}
        {m && (m.resolved.length > 0 || m.improved.length > 0 || m.new.length > 0 || m.worsened.length > 0) && (
          <div className="grid gap-3 sm:grid-cols-2">
            <MistakeGroup
              title="Cleared"
              tone="emerald"
              items={m.resolved}
              icon={<CheckCircle2 className="h-4 w-4" />}
              render={(it) => `${it.label}: ${it.from} → 0`}
            />
            <MistakeGroup
              title="Fewer"
              tone="emerald"
              items={m.improved}
              icon={<TrendingDown className="h-4 w-4" />}
              render={(it) => `${it.label}: ${it.from} → ${it.to}`}
            />
            <MistakeGroup
              title="More"
              tone="amber"
              items={m.worsened}
              icon={<TrendingUp className="h-4 w-4" />}
              render={(it) => `${it.label}: ${it.from} → ${it.to}`}
            />
            <MistakeGroup
              title="New"
              tone="amber"
              items={m.new}
              icon={<AlertCircle className="h-4 w-4" />}
              render={(it) => `${it.label}: ${it.to}`}
            />
          </div>
        )}

        {/* blocker shift */}
        {data.blocker && (
          <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm">
            {data.blocker.changed ? (
              <p className="text-[var(--text-primary)]">
                <span className="font-semibold">Main blocker changed:</span> {data.blocker.from}{" "}
                <ArrowRight className="inline h-3.5 w-3.5 text-slate-400" /> {data.blocker.to}.{" "}
                <span className="text-[var(--text-secondary)]">{data.blocker.from} is no longer your primary limitation.</span>
              </p>
            ) : (
              data.blocker.to && (
                <p className="text-[var(--text-secondary)]">
                  <span className="font-semibold text-[var(--text-primary)]">Still your main blocker:</span>{" "}
                  {data.blocker.to}.
                </p>
              )
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function BandPill({
  label,
  value,
  muted,
  highlight,
}: {
  label: string;
  value?: number | null;
  muted?: boolean;
  highlight?: boolean;
}) {
  return (
    <div className="text-center">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">{label}</p>
      <div
        className={`flex h-20 w-20 items-center justify-center rounded-2xl text-3xl font-extrabold ${
          highlight
            ? "bg-[var(--brand)] text-white shadow-[0_12px_30px_-12px_rgba(37,99,235,0.6)]"
            : muted
              ? "bg-slate-100 text-slate-400"
              : "bg-slate-100 text-[var(--text-primary)]"
        }`}
      >
        {value != null ? value.toFixed(1) : "—"}
      </div>
    </div>
  );
}

function MistakeGroup({
  title,
  tone,
  items,
  icon,
  render,
}: {
  title: string;
  tone: "emerald" | "amber";
  items: ProgressMistakeItem[];
  icon: React.ReactNode;
  render: (it: ProgressMistakeItem) => string;
}) {
  if (items.length === 0) return null;
  const color = tone === "emerald" ? "text-emerald-600" : "text-amber-600";
  return (
    <div className="rounded-xl border border-[var(--border)] p-3.5">
      <div className={`mb-2 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide ${color}`}>
        {icon}
        {title}
      </div>
      <ul className="space-y-1">
        {items.map((it) => (
          <li key={it.category} className="text-sm text-[var(--text-primary)]">
            {render(it)}
          </li>
        ))}
      </ul>
    </div>
  );
}
