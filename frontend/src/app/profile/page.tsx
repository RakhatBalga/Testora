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
  Target,
  Trophy,
  UserRound,
} from "lucide-react";
import {
  api,
  type AttemptSummary,
  type SpeakingSubmissionSummary,
  type UserProfile,
  type WritingSubmissionSummary,
} from "@/shared/api";
import { useAuth } from "@/shared/auth";
import { useRequireAuth } from "@/shared/auth";
import { IELTS_BAND_OPTIONS, IELTS_TARGET_BAND } from "@/shared/config";
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

const TOMORROW = new Date(Date.now() + 86400000).toISOString().slice(0, 10);

export default function ProfilePage() {
  const { token, ready } = useRequireAuth();
  const { username, logout } = useAuth();
  const router = useRouter();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [writing, setWriting] = useState<WritingSubmissionSummary[]>([]);
  const [speaking, setSpeaking] = useState<SpeakingSubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingTarget, setSavingTarget] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [resettingPlan, setResettingPlan] = useState(false);
  const [error, setError] = useState("");
  const [targetError, setTargetError] = useState("");

  useEffect(() => {
    if (!token) return;
    let active = true;

    Promise.all([
      api.getProfile(),
      api.listAttempts(),
      api.listWritingSubmissions(),
      api.listSpeakingSubmissions(),
    ])
      .then(([p, a, w, s]) => {
        if (!active) return;
        setProfile(p);
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
  const targetBand = profile?.target_band ?? IELTS_TARGET_BAND;

  const recentItems = useMemo<RecentItem[]>(() => {
    const readingListening = attempts.map((a) => ({
      id: `attempt-${a.id}`,
      title: a.test_title,
      meta: `${a.test_type} - ${formatDate(a.created_at)}`,
      href: a.test_type === "listening" ? `/listening/result/${a.id}` : `/result/${a.id}`,
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

  const handleTargetChange = async (band: number) => {
    if (savingTarget || band === targetBand) return;
    if (profile?.current_level !== null && profile?.current_level !== undefined && band < profile.current_level) {
      setTargetError("Target band cannot be below your current level.");
      return;
    }
    const previous = profile;
    setTargetError("");
    setSavingTarget(true);
    if (previous) setProfile({ ...previous, target_band: band });
    try {
      const updated = await api.updateProfile(band);
      setProfile(updated);
    } catch (err) {
      if (previous) setProfile(previous);
      setTargetError(err instanceof Error ? err.message : "Target band failed to save.");
    } finally {
      setSavingTarget(false);
    }
  };

  const handleSettingsSave = async () => {
    if (!profile || savingSettings) return;
    setSavingSettings(true);
    setTargetError("");
    try {
      setProfile(await api.updateProfile({
        current_level: profile.current_level,
        exam_date: profile.exam_date,
        weekly_study_days: profile.weekly_study_days,
        daily_study_minutes: profile.daily_study_minutes,
        primary_focus: profile.primary_focus,
        onboarding_completed: true,
      }));
    } catch (err) {
      setTargetError(err instanceof Error ? err.message : "Study settings failed to save.");
    } finally {
      setSavingSettings(false);
    }
  };

  const handlePlanReset = async () => {
    if (!window.confirm("Reset this week's study plan and its completion status?")) return;
    setResettingPlan(true);
    setTargetError("");
    try {
      await api.resetStudyPlan();
    } catch (err) {
      setTargetError(err instanceof Error ? err.message : "Study plan failed to reset.");
    } finally {
      setResettingPlan(false);
    }
  };

  if (!ready || !token) return null;

  return (
    <div className="space-y-6">
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand)] text-xl font-bold text-white">
              {(profile?.username ?? username)?.[0]?.toUpperCase() ?? "?"}
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Profile
              </p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                {profile?.username ?? username ?? "Student"}
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
      {targetError && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{targetError}</p>}

      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:40ms]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <Target className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Target band
              </p>
              <p className="mt-1 text-2xl font-extrabold tracking-tight text-[var(--text-primary)]">
                {loading ? "..." : targetBand.toFixed(1)}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-2 sm:flex sm:flex-wrap sm:justify-end">
            {IELTS_BAND_OPTIONS.map((band) => {
              const active = band === targetBand;
              return (
                <button
                  key={band}
                  type="button"
                  aria-pressed={active}
                  disabled={loading || savingTarget}
                  onClick={() => handleTargetChange(band)}
                  className={`h-10 min-w-14 rounded-lg border px-3 text-sm font-semibold transition ${
                    active
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950"
                  } disabled:cursor-not-allowed disabled:opacity-60`}
                >
                  {band.toFixed(1)}
                </button>
              );
            })}
          </div>
        </div>
        {savingTarget && (
          <p className="mt-3 text-sm text-[var(--text-secondary)]">Saving target...</p>
        )}
      </section>

      {profile && (
        <section className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><h2 className="font-semibold text-slate-900">Study settings</h2><p className="mt-1 text-sm text-slate-500">Used for your diagnostic baseline and weekly plan.</p></div>
            <div className="flex flex-wrap gap-2"><Button variant="secondary" disabled={resettingPlan} onClick={handlePlanReset}>{resettingPlan ? "Resetting..." : "Reset plan"}</Button><Button disabled={savingSettings} onClick={handleSettingsSave}>{savingSettings ? "Saving..." : "Save settings"}</Button></div>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <label className="text-sm font-medium text-slate-700">Current level
              <select value={profile.current_level ?? ""} onChange={(event) => setProfile({ ...profile, current_level: event.target.value ? Number(event.target.value) : null })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900">
                <option value="">Not sure</option>
                {Array.from({ length: 10 }, (_, index) => 4 + index * 0.5).map((band) => <option key={band} value={band}>{band.toFixed(1)}</option>)}
              </select>
            </label>
            <label className="text-sm font-medium text-slate-700">Exam date
              <input type="date" min={TOMORROW} value={profile.exam_date ?? ""} onChange={(event) => setProfile({ ...profile, exam_date: event.target.value || null })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900" />
            </label>
            <label className="text-sm font-medium text-slate-700">Primary focus
              <select value={profile.primary_focus} onChange={(event) => setProfile({ ...profile, primary_focus: event.target.value as UserProfile["primary_focus"] })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 capitalize text-slate-900">
                {(["writing", "reading", "speaking", "balanced"] as const).map((focus) => <option key={focus} value={focus}>{focus}</option>)}
              </select>
            </label>
            <label className="text-sm font-medium text-slate-700">Study days per week
              <input type="number" min={1} max={7} value={profile.weekly_study_days} onChange={(event) => setProfile({ ...profile, weekly_study_days: Number(event.target.value) })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900" />
            </label>
            <label className="text-sm font-medium text-slate-700">Minutes per day
              <select value={profile.daily_study_minutes} onChange={(event) => setProfile({ ...profile, daily_study_minutes: Number(event.target.value) as UserProfile["daily_study_minutes"] })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900">
                {[15, 30, 45, 60, 90].map((minutes) => <option key={minutes} value={minutes}>{minutes} minutes</option>)}
              </select>
            </label>
          </div>
          <Link href="/diagnostic" className="mt-5 inline-flex text-sm font-semibold text-[var(--brand)] hover:underline">Review diagnostic</Link>
        </section>
      )}

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
