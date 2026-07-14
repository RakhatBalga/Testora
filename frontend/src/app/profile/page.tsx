"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpen,
  CalendarDays,
  Gauge,
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
  mediaUrl,
  type AttemptSummary,
  type SpeakingSubmissionSummary,
  type UserProfile,
  type WritingSubmissionSummary,
} from "@/shared/api";
import { useAuth } from "@/shared/auth";
import { useRequireAuth } from "@/shared/auth";
import { AvatarCropper } from "@/features/avatar-crop";
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

// Used to translate saved vocabulary into the learner's first language.
const NATIVE_LANGUAGES = [
  "Russian",
  "Kazakh",
  "Uzbek",
  "Kyrgyz",
  "Turkish",
  "Azerbaijani",
  "Arabic",
  "Ukrainian",
  "Tajik",
  "Persian",
  "Other",
];

export default function ProfilePage() {
  const { token, ready } = useRequireAuth();
  const { username, logout, setAvatar } = useAuth();
  const router = useRouter();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [writing, setWriting] = useState<WritingSubmissionSummary[]>([]);
  const [speaking, setSpeaking] = useState<SpeakingSubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingTarget, setSavingTarget] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [savingAvatar, setSavingAvatar] = useState(false);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const avatarInputRef = useRef<HTMLInputElement>(null);
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

  const skillBands = useMemo(() => {
    const avg = (values: (number | null)[]): number | null => {
      const graded = values.filter((b): b is number => b !== null);
      return graded.length === 0
        ? null
        : roundHalf(graded.reduce((sum, band) => sum + band, 0) / graded.length);
    };
    return {
      reading: avg(attempts.filter((a) => a.test_type === "reading").map((a) => a.band)),
      listening: avg(attempts.filter((a) => a.test_type === "listening").map((a) => a.band)),
      writing: avg(writing.map((w) => w.band)),
      speaking: avg(speaking.map((s) => s.band)),
    };
  }, [attempts, writing, speaking]);

  const activity = useMemo(() => {
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

    const counts = new Map<string, number>();
    const bump = (iso: string | null) => {
      if (!iso) return;
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return;
      const key = fmt(d);
      counts.set(key, (counts.get(key) ?? 0) + 1);
    };
    attempts.forEach((a) => bump(a.created_at));
    writing.forEach((w) => bump(w.created_at));
    speaking.forEach((s) => bump(s.created_at));

    const WEEKS = 18;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const start = new Date(today);
    start.setDate(start.getDate() - (WEEKS * 7 - 1));
    start.setDate(start.getDate() - start.getDay()); // rewind to Sunday for aligned columns

    type Cell = { key: string; count: number; future: boolean };
    const weeks: Cell[][] = [];
    let week: Cell[] = [];
    let total = 0;
    const cursor = new Date(start);
    for (let guard = 0; guard < 400; guard += 1) {
      const cur = new Date(cursor);
      const future = cur > today;
      const count = future ? 0 : counts.get(fmt(cur)) ?? 0;
      if (!future) total += count;
      week.push({ key: fmt(cur), count, future });
      if (week.length === 7) {
        weeks.push(week);
        week = [];
      }
      const isSaturday = cur.getDay() === 6;
      cursor.setDate(cursor.getDate() + 1);
      if (isSaturday && cur >= today) break;
    }

    const flat = weeks.flat().filter((c) => !c.future);
    let activeDays = 0;
    let maxStreak = 0;
    let run = 0;
    flat.forEach((c) => {
      if (c.count > 0) {
        activeDays += 1;
        run += 1;
        maxStreak = Math.max(maxStreak, run);
      } else {
        run = 0;
      }
    });
    let currentStreak = 0;
    for (let i = flat.length - 1; i >= 0; i -= 1) {
      if (flat[i].count > 0) currentStreak += 1;
      else break;
    }

    return { weeks, total, activeDays, maxStreak, currentStreak, windowWeeks: weeks.length };
  }, [attempts, writing, speaking]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const handleAvatarSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-selecting the same file later
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setTargetError("Avatar must be an image file.");
      return;
    }
    setTargetError("");
    setCropFile(file); // open the cropper; upload happens on save
  };

  const handleCropSave = async (blob: Blob) => {
    if (savingAvatar) return;
    setSavingAvatar(true);
    try {
      const file = new File([blob], "avatar.jpg", { type: "image/jpeg" });
      const updated = await api.uploadAvatar(file);
      setProfile((prev) => (prev ? { ...prev, avatar: updated.avatar } : updated));
      setAvatar(updated.avatar);
      setCropFile(null);
    } catch (err) {
      setTargetError(err instanceof Error ? err.message : "Avatar failed to upload.");
    } finally {
      setSavingAvatar(false);
    }
  };

  const handleAvatarRemove = async () => {
    if (!profile?.avatar || savingAvatar) return;
    setTargetError("");
    setSavingAvatar(true);
    try {
      const updated = await api.deleteAvatar();
      setProfile((prev) => (prev ? { ...prev, avatar: updated.avatar } : updated));
      setAvatar(updated.avatar);
    } catch (err) {
      setTargetError(err instanceof Error ? err.message : "Avatar failed to remove.");
    } finally {
      setSavingAvatar(false);
    }
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
        native_language: profile.native_language,
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
      {cropFile && (
        <AvatarCropper
          file={cropFile}
          saving={savingAvatar}
          onCancel={() => setCropFile(null)}
          onSave={handleCropSave}
        />
      )}
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            {profile?.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaUrl(profile.avatar) ?? undefined}
                alt="Your avatar"
                className="h-14 w-14 rounded-full object-cover ring-2 ring-[var(--brand)]/15 ring-offset-2 ring-offset-white"
              />
            ) : (
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--brand)] text-xl font-bold text-white ring-2 ring-[var(--brand)]/15 ring-offset-2 ring-offset-white">
                {(profile?.username ?? username)?.[0]?.toUpperCase() ?? "?"}
              </span>
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Profile
              </p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                {profile?.username ?? username ?? "Student"}
              </h1>
              <p className="mt-0.5 text-sm font-medium text-[var(--text-secondary)]">
                {loading
                  ? "..."
                  : `${totalSessions} session${totalSessions === 1 ? "" : "s"} · Target band ${targetBand.toFixed(1)}`}
              </p>
              {profile && (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <input
                    ref={avatarInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleAvatarSelect}
                  />
                  <button
                    type="button"
                    disabled={savingAvatar}
                    onClick={() => avatarInputRef.current?.click()}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {savingAvatar ? "Saving..." : profile.avatar ? "Change photo" : "Upload photo"}
                  </button>
                  {profile.avatar && (
                    <button
                      type="button"
                      disabled={savingAvatar}
                      onClick={handleAvatarRemove}
                      className="rounded-lg px-2 py-1.5 text-sm font-medium text-slate-500 transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Remove
                    </button>
                  )}
                </div>
              )}
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
        <div className="mb-5 flex items-center gap-2">
          <Gauge className="h-5 w-5 text-[var(--brand)]" />
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Band snapshot</h2>
        </div>

        {loading ? (
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
            <Skeleton className="mx-auto h-36 w-36 shrink-0 rounded-full sm:mx-0" />
            <div className="flex-1 space-y-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-6 w-full rounded-lg" />
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
              <div className="relative mx-auto h-36 w-36 shrink-0 sm:mx-0">
                <BandRing value={avgBand} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
                    {avgBand === null ? "-" : avgBand.toFixed(1)}
                  </span>
                  <span className="text-xs font-medium text-[var(--text-secondary)]">of 9.0</span>
                </div>
              </div>
              <div className="w-full flex-1 space-y-3">
                <SkillBandBar label="Reading" band={skillBands.reading} />
                <SkillBandBar label="Listening" band={skillBands.listening} />
                <SkillBandBar label="Writing" band={skillBands.writing} />
                <SkillBandBar label="Speaking" band={skillBands.speaking} />
              </div>
            </div>
            <p className="mt-5 text-sm text-[var(--text-secondary)]">
              {avgBand === null
                ? "Complete a graded test to see your average band."
                : avgBand >= targetBand
                  ? `You're at or above your target of ${targetBand.toFixed(1)}. Keep it steady.`
                  : `${(targetBand - avgBand).toFixed(1)} band to reach your target of ${targetBand.toFixed(1)}.`}
            </p>
          </>
        )}
      </section>

      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:60ms]">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-[var(--brand)]" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Activity</h2>
          </div>
          {!loading && (
            <p className="text-sm text-[var(--text-secondary)]">
              Active days: <span className="font-semibold text-[var(--text-primary)]">{activity.activeDays}</span>
              <span className="px-2 text-slate-300">·</span>
              Current streak: <span className="font-semibold text-[var(--text-primary)]">{activity.currentStreak}</span>
              <span className="px-2 text-slate-300">·</span>
              Best streak: <span className="font-semibold text-[var(--text-primary)]">{activity.maxStreak}</span>
            </p>
          )}
        </div>

        {loading ? (
          <Skeleton className="h-28 w-full rounded-xl" />
        ) : (
          <>
            <p className="mb-4 text-sm text-[var(--text-secondary)]">
              <span className="font-semibold text-[var(--text-primary)]">{activity.total}</span> session
              {activity.total === 1 ? "" : "s"} in the last {activity.windowWeeks} weeks
            </p>
            <div className="overflow-x-auto pb-1">
              <div className="flex gap-1">
                {activity.weeks.map((week, wi) => (
                  <div key={wi} className="flex flex-col gap-1">
                    {week.map((cell, di) => (
                      <span
                        key={cell.key || `${wi}-${di}`}
                        title={cell.future ? undefined : `${cell.count} session${cell.count === 1 ? "" : "s"} · ${cell.key}`}
                        className={`h-3 w-3 rounded-[3px] ${heatClass(cell.count, cell.future)}`}
                      />
                    ))}
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 flex items-center justify-end gap-1.5 text-xs text-[var(--text-secondary)]">
              <span>Less</span>
              <span className="h-3 w-3 rounded-[3px] bg-slate-100" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]/30" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]/55" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]/80" />
              <span className="h-3 w-3 rounded-[3px] bg-[var(--brand)]" />
              <span>More</span>
            </div>
          </>
        )}
      </section>

      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:80ms]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex shrink-0 items-center justify-center text-[var(--brand)]">
              <Target className="h-6 w-6" />
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
                  className={`h-10 min-w-0 rounded-lg border px-2 text-sm font-semibold transition sm:min-w-14 sm:px-3 ${
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
            <div><h2 className="font-semibold text-slate-900">Study settings</h2><p className="mt-1 text-sm text-slate-500">Used for your weekly plan.</p></div>
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
            <label className="text-sm font-medium text-slate-700">Native language
              <select value={profile.native_language ?? ""} onChange={(event) => setProfile({ ...profile, native_language: event.target.value || null })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900">
                <option value="">Not set</option>
                {NATIVE_LANGUAGES.map((lang) => <option key={lang} value={lang}>{lang}</option>)}
              </select>
              <span className="mt-1 block text-xs font-normal text-slate-400">Used to translate saved vocabulary.</span>
            </label>
          </div>
        </section>
      )}

      <section className="grid animate-fade-up grid-cols-2 gap-3 [animation-delay:60ms] sm:gap-4 lg:grid-cols-4">
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
              <SkillRow icon={<BookOpen className="h-5 w-5" />} label="Reading" value={readingCount} href="/tests/reading" />
              <SkillRow icon={<Headphones className="h-5 w-5" />} label="Listening" value={listeningCount} href="/tests/listening" />
              <SkillRow icon={<PenLine className="h-5 w-5" />} label="Writing" value={writing.length} href="/writing" />
              <SkillRow icon={<Mic className="h-5 w-5" />} label="Speaking" value={speaking.length} href="/speaking" />
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

function heatClass(count: number, future: boolean): string {
  if (future) return "bg-transparent";
  if (count <= 0) return "bg-slate-100";
  if (count === 1) return "bg-[var(--brand)]/30";
  if (count === 2) return "bg-[var(--brand)]/55";
  if (count === 3) return "bg-[var(--brand)]/80";
  return "bg-[var(--brand)]";
}

function BandRing({ value }: { value: number | null }) {
  const max = 9;
  const pct = value === null ? 0 : Math.min(Math.max(value / max, 0), 1);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const dash = circumference * pct;
  return (
    <svg viewBox="0 0 120 120" className="h-36 w-36 -rotate-90">
      <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--border)" strokeWidth="10" />
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke="var(--brand)"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circumference}`}
        className="transition-[stroke-dasharray] duration-700 ease-out"
      />
    </svg>
  );
}

function SkillBandBar({ label, band }: { label: string; band: number | null }) {
  const pct = band === null ? 0 : Math.min(Math.max(band / 9, 0), 1) * 100;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-[var(--text-primary)]">{label}</span>
        <span className="font-semibold text-[var(--text-secondary)]">
          {band === null ? "-" : band.toFixed(1)}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-[var(--brand)] transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ProfileMetric({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm shadow-slate-200/40 before:absolute before:inset-y-0 before:left-0 before:w-1 before:bg-[var(--brand)] sm:p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {label}
      </p>
      {value === null ? (
        <Skeleton className="mt-2 h-9 w-16 rounded-lg" />
      ) : (
        <p className="mt-1 text-2xl font-extrabold tracking-tight text-[var(--text-primary)] sm:text-3xl">
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
        <span className="flex h-8 w-8 items-center justify-center text-[var(--brand)]">
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
