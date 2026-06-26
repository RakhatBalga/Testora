"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpen,
  Headphones,
  LogOut,
  Mic,
  PenLine,
  Trophy,
  UserRound,
} from "lucide-react";
import {
  api,
  type AttemptSummary,
  type SpeakingSubmissionSummary,
  type WritingSubmissionSummary,
} from "@/shared/api";
import { useAuth } from "@/shared/auth";
import { useRequireAuth } from "@/shared/auth";
import { Button, LinkButton } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

function roundHalf(n: number): number {
  return Math.round(n * 2) / 2;
}

function formatDate(value: string | null): string {
  if (!value) return "No date";
  return new Date(value).toLocaleDateString();
}

function bandTone(band: number | null): string {
  if (band === null) return "bg-slate-100 text-slate-500";
  if (band >= 7) return "bg-emerald-50 text-emerald-700";
  if (band >= 5.5) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

function scoreTone(score: number, total: number): string {
  const pct = total > 0 ? (score / total) * 100 : 0;
  if (pct >= 70) return "bg-emerald-50 text-emerald-700";
  if (pct >= 40) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

type RecentItem = {
  id: string;
  title: string;
  meta: string;
  href: string;
  badge: string;
  badgeClass: string;
  createdAt: string | null;
};

export default function ProfilePage() {
  const { token, ready } = useRequireAuth();
  const { username, logout } = useAuth();
  const router = useRouter();

  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [writing, setWriting] = useState<WritingSubmissionSummary[]>([]);
  const [speaking, setSpeaking] = useState<SpeakingSubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    let active = true;

    Promise.all([
      api.listAttempts(),
      api.listWritingSubmissions(),
      api.listSpeakingSubmissions(),
    ])
      .then(([a, w, s]) => {
        if (!active) return;
        setAttempts(a);
        setWriting(w);
        setSpeaking(s);
      })
      .catch((err) => active && setError(err.message || "Profile failed to load."))
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [token]);

  const readingCount = attempts.filter((a) => a.test_type === "reading").length;
  const listeningCount = attempts.filter((a) => a.test_type === "listening").length;
  const totalSessions = attempts.length + writing.length + speaking.length;

  const bands = [
    ...attempts.map((a) => a.band),
    ...writing.map((w) => w.band),
    ...speaking.map((s) => s.band),
  ].filter((b): b is number => b !== null);

  const avgBand =
    bands.length === 0
      ? null
      : roundHalf(bands.reduce((sum, band) => sum + band, 0) / bands.length);
  const bestBand = bands.length === 0 ? null : Math.max(...bands);

  const recentItems = useMemo<RecentItem[]>(() => {
    const readingListening = attempts.map((a) => ({
      id: `attempt-${a.id}`,
      title: a.test_title,
      meta: `${a.test_type} - ${formatDate(a.created_at)}`,
      href: `/result/${a.id}`,
      badge: `${a.score}/${a.total}`,
      badgeClass: scoreTone(a.score, a.total),
      createdAt: a.created_at,
    }));

    const writingItems = writing.map((w) => ({
      id: `writing-${w.id}`,
      title: w.task_title,
      meta: `${w.word_count} words - ${formatDate(w.created_at)}`,
      href: `/writing/result/${w.id}`,
      badge: w.band === null ? w.status : `Band ${w.band.toFixed(1)}`,
      badgeClass: bandTone(w.band),
      createdAt: w.created_at,
    }));

    const speakingItems = speaking.map((s) => ({
      id: `speaking-${s.id}`,
      title: `Speaking Part ${s.task_part}`,
      meta: formatDate(s.created_at),
      href: `/speaking/result/${s.id}`,
      badge: s.band === null ? "submitted" : `Band ${s.band.toFixed(1)}`,
      badgeClass: bandTone(s.band),
      createdAt: s.created_at,
    }));

    return [...readingListening, ...writingItems, ...speakingItems]
      .sort((a, b) => {
        const at = a.createdAt ? new Date(a.createdAt).getTime() : 0;
        const bt = b.createdAt ? new Date(b.createdAt).getTime() : 0;
        return bt - at;
      })
      .slice(0, 6);
  }, [attempts, writing, speaking]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (!ready || !token) return null;

  return (
    <div className="space-y-6">
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand)] text-xl font-bold text-white">
              {username?.[0]?.toUpperCase() ?? "?"}
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Profile
              </p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                {username ?? "Student"}
              </h1>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <LinkButton href="/analytics" variant="secondary">
              <BarChart3 className="h-4 w-4" />
              Analytics
            </LinkButton>
            <Button variant="secondary" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        </div>
      </section>

      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      <section className="grid animate-fade-up gap-4 [animation-delay:60ms] sm:grid-cols-2 lg:grid-cols-4">
        <ProfileMetric label="Sessions" value={loading ? null : String(totalSessions)} />
        <ProfileMetric
          label="Average band"
          value={loading ? null : avgBand === null ? "-" : avgBand.toFixed(1)}
        />
        <ProfileMetric
          label="Best band"
          value={loading ? null : bestBand === null ? "-" : bestBand.toFixed(1)}
        />
        <ProfileMetric label="AI reviews" value={loading ? null : String(writing.length + speaking.length)} />
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:100ms]">
          <div className="mb-5 flex items-center gap-2">
            <Activity className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Practice record</h2>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14 w-full rounded-xl" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              <SkillRow icon={<BookOpen className="h-4 w-4" />} label="Reading" value={readingCount} href="/tests/reading" />
              <SkillRow icon={<Headphones className="h-4 w-4" />} label="Listening" value={listeningCount} href="/tests/listening" />
              <SkillRow icon={<PenLine className="h-4 w-4" />} label="Writing" value={writing.length} href="/writing" />
              <SkillRow icon={<Mic className="h-4 w-4" />} label="Speaking" value={speaking.length} href="/speaking" />
            </div>
          )}
        </section>

        <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:140ms]">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Trophy className="h-5 w-5 text-amber-500" />
              <h2 className="text-base font-semibold text-[var(--text-primary)]">Recent activity</h2>
            </div>
            <Link href="/practice" className="text-sm font-semibold text-[var(--brand)]">
              Practice
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-14 w-full rounded-xl" />
              ))}
            </div>
          ) : recentItems.length > 0 ? (
            <div className="space-y-2.5">
              {recentItems.map((item) => (
                <RecentRow key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-[var(--border)] bg-slate-50/60 p-6 text-center">
              <UserRound className="mx-auto h-7 w-7 text-slate-300" />
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                Your completed tests and AI reviews will appear here.
              </p>
              <LinkButton href="/practice" size="sm" className="mt-4">
                Start practice
              </LinkButton>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function ProfileMetric({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm shadow-slate-200/40">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {label}
      </p>
      {value === null ? (
        <Skeleton className="mt-2 h-9 w-16 rounded-lg" />
      ) : (
        <p className="mt-1 text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
          {value}
        </p>
      )}
    </div>
  );
}

function SkillRow({
  icon,
  label,
  value,
  href,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center justify-between rounded-xl border border-[var(--border)] px-4 py-3 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <span className="flex items-center gap-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-[var(--text-secondary)]">
          {icon}
        </span>
        <span className="text-sm font-semibold text-[var(--text-primary)]">{label}</span>
      </span>
      <span className="flex items-center gap-2 text-sm font-semibold text-[var(--text-secondary)]">
        {value}
        <ArrowRight className="h-4 w-4 text-slate-300 transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
      </span>
    </Link>
  );
}

function RecentRow({ item }: { item: RecentItem }) {
  return (
    <Link
      href={item.href}
      className="group flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] px-4 py-3 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-[var(--text-primary)]">
          {item.title}
        </span>
        <span className="mt-0.5 block text-xs capitalize text-[var(--text-secondary)]">
          {item.meta}
        </span>
      </span>
      <span className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-semibold capitalize ${item.badgeClass}`}>
        {item.badge}
      </span>
    </Link>
  );
}
