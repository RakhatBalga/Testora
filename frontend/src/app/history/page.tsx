"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  History,
  ArrowUpRight,
  SlidersHorizontal,
  GitCompare,
  X,
} from "lucide-react";
import { useRequireAuth } from "@/shared/auth";
import { api, type HistoryItem } from "@/shared/api";
import { PageHeader } from "@/shared/ui/dashboard";
import { useRouter } from "next/navigation";

type Skill = "all" | "writing" | "speaking" | "reading" | "listening";
type Sort = "newest" | "oldest" | "highest" | "lowest";

const SKILL_TABS: { value: Skill; label: string }[] = [
  { value: "all", label: "All" },
  { value: "writing", label: "Writing" },
  { value: "speaking", label: "Speaking" },
  { value: "reading", label: "Reading" },
  { value: "listening", label: "Listening" },
];

const SORT_OPTIONS: { value: Sort; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "highest", label: "Highest band" },
  { value: "lowest", label: "Lowest band" },
];

const SKILL_COLORS: Record<string, string> = {
  writing: "bg-blue-50 text-blue-700 border-blue-200",
  speaking: "bg-emerald-50 text-emerald-700 border-emerald-200",
  reading: "bg-amber-50 text-amber-700 border-amber-200",
  listening: "bg-violet-50 text-violet-700 border-violet-200",
};

function bandTone(band: number | null): string {
  if (band === null) return "text-slate-400";
  if (band >= 7) return "text-emerald-600";
  if (band >= 5.5) return "text-amber-600";
  return "text-red-600";
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export default function HistoryPage() {
  const { token, ready } = useRequireAuth();
  const router = useRouter();

  const [skillFilter, setSkillFilter] = useState<Skill>("all");
  const [sort, setSort] = useState<Sort>("newest");
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    if (!token) return;
    const timer = window.setTimeout(() => {
      setItems(null);
      setError(null);
      setSelected([]);
      api
        .getHistory(skillFilter === "all" ? undefined : skillFilter, sort)
        .then((r) => setItems(r.items))
        .catch((e) => {
          setError(e.message);
          setItems([]);
        });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [token, skillFilter, sort]);

  const toggleSelect = (item: HistoryItem) => {
    setSelected((prev) => {
      if (prev.includes(item.id)) return prev.filter((x) => x !== item.id);
      // Only allow same skill comparison
      const prevSkill = prev[0]?.split("-")[0];
      if (prevSkill && prevSkill !== item.skill) return prev;
      if (prev.length >= 2) return [prev[1], item.id];
      return [...prev, item.id];
    });
  };

  const canCompare = selected.length === 2;

  const handleCompare = () => {
    if (canCompare) {
      router.push(`/history/compare?a=${selected[0]}&b=${selected[1]}`);
    }
  };

  if (!ready || !token) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attempt History"
        subtitle="Every practice session and test result in one place."
        action={
          selected.length > 0 ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-[var(--text-secondary)]">
                {selected.length} selected
                {selected.length === 1 ? " — pick one more to compare" : ""}
              </span>
              {canCompare && (
                <button
                  onClick={handleCompare}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                >
                  <GitCompare className="h-4 w-4" />
                  Compare
                </button>
              )}
              <button
                onClick={() => setSelected([])}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:bg-slate-50"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : null
        }
      />

      {/* Filter + Sort bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          {SKILL_TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => setSkillFilter(t.value)}
              className={`rounded-xl px-3.5 py-1.5 text-sm font-medium transition-colors ${
                skillFilter === t.value
                  ? "bg-[var(--brand)] text-white"
                  : "border border-[var(--border)] bg-white text-[var(--text-secondary)] hover:border-slate-300 hover:text-[var(--text-primary)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
          <SlidersHorizontal className="h-4 w-4" />
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as Sort)}
            className="rounded-lg border border-[var(--border)] bg-white px-2.5 py-1.5 text-sm font-medium text-[var(--text-primary)] outline-none hover:border-slate-300"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Compare hint */}
      {selected.length === 0 && (items?.length ?? 0) >= 2 && (
        <p className="text-xs text-[var(--text-secondary)]">
          Tip: click any two attempts of the same skill to compare them side by side.
        </p>
      )}

      {/* List */}
      {items === null ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl border border-[var(--border)] bg-slate-50" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-600">{error}</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-[var(--border)] py-14 text-center">
          <History className="h-8 w-8 text-slate-300" />
          <p className="text-sm text-[var(--text-secondary)]">
            {skillFilter === "all"
              ? "No attempts yet. Start a Writing task or a Reading test to see your history here."
              : `No ${skillFilter} attempts yet.`}
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {items.map((item) => {
            const isSelected = selected.includes(item.id);
            const prevSkill = selected[0]?.split("-")[0];
            const isDisabled = selected.length > 0 && prevSkill !== item.skill && !isSelected;
            return (
              <HistoryRow
                key={item.id}
                item={item}
                isSelected={isSelected}
                isDisabled={isDisabled}
                onSelect={() => toggleSelect(item)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function HistoryRow({
  item,
  isSelected,
  isDisabled,
  onSelect,
}: {
  item: HistoryItem;
  isSelected: boolean;
  isDisabled: boolean;
  onSelect: () => void;
}) {
  const skillClass = SKILL_COLORS[item.skill] ?? "bg-slate-100 text-slate-600 border-slate-200";
  const tone = bandTone(item.band);

  return (
    <div
      className={`flex items-center gap-4 rounded-2xl border p-4 transition-colors ${
        isSelected
          ? "border-[var(--brand)] bg-[var(--brand)]/[0.04]"
          : isDisabled
            ? "border-[var(--border)] bg-slate-50 opacity-50"
            : "border-[var(--border)] bg-white hover:border-slate-300"
      }`}
    >
      {/* Checkbox */}
      <button
        onClick={onSelect}
        disabled={isDisabled}
        className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded border-2 transition-colors ${
          isSelected ? "border-[var(--brand)] bg-[var(--brand)]" : "border-slate-300"
        } disabled:cursor-not-allowed`}
        aria-label={isSelected ? "Deselect" : "Select for comparison"}
      >
        {isSelected && (
          <svg className="h-3 w-3 text-white" viewBox="0 0 12 12" fill="none">
            <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </button>

      {/* Skill badge */}
      <span className={`flex-shrink-0 rounded-lg border px-2.5 py-1 text-xs font-semibold capitalize ${skillClass}`}>
        {item.skill}
      </span>

      {/* Title + date */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{item.title}</p>
        <p className="text-xs text-[var(--text-secondary)]">{fmtDate(item.created_at)}</p>
      </div>

      {/* Score */}
      {item.score != null && item.total != null && (
        <span className="flex-shrink-0 text-sm font-medium text-[var(--text-secondary)]">
          {item.score}/{item.total}
        </span>
      )}

      {/* Band */}
      <span className={`flex-shrink-0 text-lg font-extrabold tabular-nums ${tone}`}>
        {item.band != null ? item.band.toFixed(1) : "—"}
      </span>

      {/* Status */}
      <span
        className={`flex-shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
          item.status === "graded"
            ? "bg-emerald-50 text-emerald-700"
            : "bg-amber-50 text-amber-700"
        }`}
      >
        {item.status}
      </span>

      {/* Link */}
      <Link
        href={item.href}
        className="flex-shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-[var(--brand)]"
        aria-label="Open attempt"
      >
        <ArrowUpRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
