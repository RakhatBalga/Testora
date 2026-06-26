"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowLeft,
  GitCompare,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { useRequireAuth } from "@/shared/auth";
import { api, type CompareResult, type CriteriaDiffItem, type QTypeDiffItem, type MistakeDiffItem } from "@/shared/api";
import { PageHeader } from "@/shared/ui/dashboard";

const SKILL_COLORS: Record<string, string> = {
  writing: "bg-blue-50 text-blue-700",
  speaking: "bg-emerald-50 text-emerald-700",
  reading: "bg-amber-50 text-amber-700",
  listening: "bg-violet-50 text-violet-700",
};

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return null;
  const up = delta > 0;
  const down = delta < 0;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold ${
        up ? "bg-emerald-50 text-emerald-600" : down ? "bg-red-50 text-red-600" : "bg-slate-100 text-slate-500"
      }`}
    >
      {up ? <TrendingUp className="h-4 w-4" /> : down ? <TrendingDown className="h-4 w-4" /> : <Minus className="h-4 w-4" />}
      {up ? "+" : ""}{delta.toFixed(1)}
    </span>
  );
}

function BandCard({ label, band, date }: { label: string; band: number | null; date: string | null }) {
  const tone =
    band === null
      ? "text-slate-400"
      : band >= 7
        ? "text-emerald-600"
        : band >= 5.5
          ? "text-amber-600"
          : "text-red-600";
  return (
    <div className="flex-1 rounded-2xl border border-[var(--border)] bg-white p-5 text-center shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">{label}</p>
      <p className={`mt-1 text-5xl font-extrabold ${tone}`}>{band != null ? band.toFixed(1) : "—"}</p>
      <p className="mt-1 text-xs text-[var(--text-secondary)]">{fmtDate(date)}</p>
    </div>
  );
}

function CriteriaDiff({ diff }: { diff: CriteriaDiffItem[] }) {
  if (!diff.length) return null;
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">Criteria comparison</h3>
      <div className="space-y-3">
        {diff.map((c) => (
          <div key={c.name} className="flex items-center gap-3">
            <span className="w-44 truncate text-sm text-[var(--text-secondary)]">{c.name}</span>
            <span className="w-10 text-right text-sm font-semibold tabular-nums text-[var(--text-secondary)]">
              {c.a.toFixed(1)}
            </span>
            <div className="flex flex-1 items-center justify-center gap-1 text-xs text-[var(--text-secondary)]">
              →
            </div>
            <span className="w-10 text-sm font-semibold tabular-nums text-[var(--text-primary)]">
              {c.b.toFixed(1)}
            </span>
            <span
              className={`ml-2 inline-flex w-16 items-center justify-center gap-1 rounded-lg px-2 py-0.5 text-xs font-semibold ${
                c.direction === "up"
                  ? "bg-emerald-50 text-emerald-600"
                  : c.direction === "down"
                    ? "bg-red-50 text-red-600"
                    : "bg-slate-100 text-slate-500"
              }`}
            >
              {c.direction === "up" ? (
                <ChevronUp className="h-3 w-3" />
              ) : c.direction === "down" ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <Minus className="h-3 w-3" />
              )}
              {c.delta > 0 ? "+" : ""}{c.delta.toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function MistakeBuckets({ mistakes }: { mistakes: CompareResult["mistakes"] }) {
  if (!mistakes) return null;
  const { resolved, improved, worsened, new: newMistakes } = mistakes;
  const hasAny = resolved.length + improved.length + worsened.length + newMistakes.length > 0;
  if (!hasAny) return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold text-[var(--text-primary)]">Mistake changes</h3>
      <p className="text-sm text-[var(--text-secondary)]">No change in mistake patterns between these two attempts.</p>
    </section>
  );

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">Mistake changes</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <MistakeGroup title="Resolved" items={resolved} icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" />} tone="text-emerald-600" />
        <MistakeGroup title="Improved" items={improved} icon={<TrendingUp className="h-4 w-4 text-emerald-500" />} tone="text-emerald-600" />
        <MistakeGroup title="Worsened" items={worsened} icon={<TrendingDown className="h-4 w-4 text-amber-500" />} tone="text-amber-600" />
        <MistakeGroup title="New" items={newMistakes} icon={<AlertCircle className="h-4 w-4 text-red-500" />} tone="text-red-600" />
      </div>
    </section>
  );
}

function MistakeGroup({
  title,
  items,
  icon,
  tone,
}: {
  title: string;
  items: MistakeDiffItem[];
  icon: React.ReactNode;
  tone: string;
}) {
  if (!items.length) return null;
  return (
    <div className="rounded-xl bg-slate-50 p-4">
      <div className="mb-2 flex items-center gap-1.5">
        {icon}
        <span className={`text-xs font-semibold ${tone}`}>{title}</span>
      </div>
      <div className="space-y-1">
        {items.map((m) => (
          <div key={m.category} className="flex items-center justify-between text-sm">
            <span className="text-[var(--text-primary)]">{m.label}</span>
            <span className="font-semibold tabular-nums text-[var(--text-secondary)]">
              {m.a} → {m.b}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function QTypeDiff({ diff }: { diff: QTypeDiffItem[] }) {
  if (!diff.length) return null;
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">Question type accuracy</h3>
      <div className="space-y-3">
        {diff.map((item) => (
          <div key={item.question_type} className="flex items-center gap-3">
            <span className="min-w-0 flex-1 truncate text-sm text-[var(--text-secondary)]">{item.label}</span>
            <span className="w-14 text-right text-sm font-semibold tabular-nums text-[var(--text-secondary)]">
              {item.a_accuracy.toFixed(0)}%
            </span>
            <span className="text-xs text-[var(--text-secondary)]">→</span>
            <span className="w-14 text-sm font-semibold tabular-nums text-[var(--text-primary)]">
              {item.b_accuracy.toFixed(0)}%
            </span>
            <span
              className={`ml-1 inline-flex w-16 items-center justify-center gap-1 rounded-lg px-2 py-0.5 text-xs font-semibold ${
                item.direction === "up"
                  ? "bg-emerald-50 text-emerald-600"
                  : item.direction === "down"
                    ? "bg-red-50 text-red-600"
                    : "bg-slate-100 text-slate-500"
              }`}
            >
              {item.direction === "up" ? (
                <ChevronUp className="h-3 w-3" />
              ) : item.direction === "down" ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <Minus className="h-3 w-3" />
              )}
              {item.delta > 0 ? "+" : ""}{item.delta.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function CompareContent() {
  const { token, ready } = useRequireAuth();
  const searchParams = useSearchParams();
  const a = searchParams?.get("a") ?? null;
  const b = searchParams?.get("b") ?? null;

  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !a || !b) return;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      api
        .compareHistory(a, b)
        .then(setResult)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [token, a, b]);

  if (!ready || !token) return null;

  if (!a || !b) {
    return (
      <div className="space-y-6">
        <PageHeader title="Compare Attempts" />
        <p className="rounded-2xl border border-[var(--border)] bg-white p-6 text-sm text-[var(--text-secondary)]">
          No attempts selected. Go to{" "}
          <Link href="/history" className="font-semibold text-[var(--brand)]">
            History
          </Link>{" "}
          and select two attempts of the same skill to compare.
        </p>
      </div>
    );
  }

  const skillClass = result ? (SKILL_COLORS[result.skill] ?? "bg-slate-100 text-slate-600") : "";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compare Attempts"
        subtitle="Side-by-side diff of two same-skill attempts."
        action={
          <Link
            href="/history"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--brand)] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to history
          </Link>
        }
      />

      {loading ? (
        <div className="space-y-4">
          <div className="h-32 animate-pulse rounded-2xl bg-slate-100" />
          <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
        </div>
      ) : error ? (
        <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-6">
          <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
          <div>
            <p className="font-semibold text-red-700">Cannot compare these attempts</p>
            <p className="mt-1 text-sm text-red-600">{error}</p>
            <Link
              href="/history"
              className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-red-700 hover:underline"
            >
              <ArrowLeft className="h-4 w-4" /> Back to history
            </Link>
          </div>
        </div>
      ) : result ? (
        <div className="space-y-5">
          {/* Header: skill + band summary */}
          <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm">
            <span className={`rounded-lg px-2.5 py-1 text-xs font-semibold capitalize ${skillClass}`}>
              {result.skill}
            </span>
            <GitCompare className="h-4 w-4 text-slate-400" />
            <span className="text-sm text-[var(--text-secondary)]">Band change</span>
            <DeltaBadge delta={result.band_delta} />
            {result.blocker?.changed && (
              <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700">
                Blocker changed: {result.blocker.a} → {result.blocker.b}
              </span>
            )}
          </div>

          {/* Band side-by-side */}
          <div className="flex gap-4">
            <BandCard label="Attempt A" band={result.a.band} date={result.a.created_at} />
            <div className="flex items-center justify-center px-2">
              <DeltaBadge delta={result.band_delta} />
            </div>
            <BandCard label="Attempt B" band={result.b.band} date={result.b.created_at} />
          </div>

          {/* Score (Reading/Listening) */}
          {(result.a as { score?: string | null }).score != null && (
            <div className="flex gap-4">
              <div className="flex-1 rounded-2xl border border-[var(--border)] bg-white p-4 text-center shadow-sm">
                <p className="text-xs text-[var(--text-secondary)]">Score A</p>
                <p className="mt-1 text-2xl font-bold text-[var(--text-primary)]">{(result.a as { score?: string | null }).score}</p>
              </div>
              <div className="flex-1 rounded-2xl border border-[var(--border)] bg-white p-4 text-center shadow-sm">
                <p className="text-xs text-[var(--text-secondary)]">Score B</p>
                <p className="mt-1 text-2xl font-bold text-[var(--text-primary)]">{(result.b as { score?: string | null }).score}</p>
              </div>
            </div>
          )}

          {/* Criteria diff (Writing/Speaking) */}
          {result.criteria_diff && <CriteriaDiff diff={result.criteria_diff} />}

          {/* Mistake buckets (Writing/Speaking) */}
          {result.mistakes && <MistakeBuckets mistakes={result.mistakes} />}

          {/* Question type diff (Reading/Listening) */}
          {result.question_type_diff && <QTypeDiff diff={result.question_type_diff} />}

          <Link
            href="/history"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--brand)] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" /> Back to history
          </Link>
        </div>
      ) : null}
    </div>
  );
}
