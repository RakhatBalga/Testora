"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, CalendarDays, Clock3, Target } from "lucide-react";
import { api, type UserProfile } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Button, Card, Skeleton } from "@/shared/ui";

const TARGETS = Array.from({ length: 9 }, (_, index) => 5 + index * 0.5);
const LEVELS = Array.from({ length: 10 }, (_, index) => 4 + index * 0.5);
const MINUTES = [15, 30, 45, 60, 90] as const;
const FOCUSES = ["writing", "reading", "speaking", "balanced"] as const;
const TOMORROW = new Date(Date.now() + 86400000).toISOString().slice(0, 10);

export function OnboardingFlow() {
  const { token, ready } = useRequireAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api.getProfile().then(setProfile).catch((err) => setError(err.message));
  }, [token]);

  if (!ready || !token) return null;
  if (!profile) return error ? <ErrorMessage message={error} /> : <Skeleton className="h-96 w-full" />;

  const update = <K extends keyof UserProfile>(key: K, value: UserProfile[K]) => {
    setProfile((current) => (current ? { ...current, [key]: value } : current));
  };
  const updateCurrentLevel = (value: number | null) => {
    setProfile((current) => current ? {
      ...current,
      current_level: value,
      target_band: value === null ? current.target_band : Math.max(current.target_band, value),
    } : current);
  };

  const finish = async () => {
    setSaving(true);
    setError("");
    try {
      await api.updateProfile({
        target_band: profile.target_band,
        current_level: profile.current_level,
        exam_date: profile.exam_date,
        weekly_study_days: profile.weekly_study_days,
        daily_study_minutes: profile.daily_study_minutes,
        primary_focus: profile.primary_focus,
        onboarding_completed: true,
      });
      router.push("/diagnostic");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your plan");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <p className="text-sm font-semibold text-[var(--brand)]">Step {step} of 3</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-950">Build your IELTS plan</h1>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
          <div className="h-full bg-[var(--brand)] transition-all" style={{ width: `${(step / 3) * 100}%` }} />
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      <Card className="p-6 sm:p-8">
        {step === 1 && (
          <div>
            <Heading icon={<Target className="h-5 w-5" />} title="Where are you heading?" />
            <FieldLabel>Target band</FieldLabel>
            <ChoiceGrid values={TARGETS} selected={profile.target_band} format={(value) => value.toFixed(1)} onSelect={(value) => update("target_band", value)} />
            <FieldLabel>Current level</FieldLabel>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
              <Choice active={profile.current_level === null} label="Not sure" onClick={() => updateCurrentLevel(null)} />
              {LEVELS.map((level) => <Choice key={level} active={profile.current_level === level} label={level.toFixed(1)} onClick={() => updateCurrentLevel(level)} />)}
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <Heading icon={<CalendarDays className="h-5 w-5" />} title="Set your schedule" />
            <label className="block text-sm font-semibold text-slate-700" htmlFor="exam-date">Exam date <span className="font-normal text-slate-400">optional</span></label>
            <input id="exam-date" type="date" min={TOMORROW} value={profile.exam_date ?? ""} onChange={(event) => update("exam_date", event.target.value || null)} className="mt-2 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20" />
            <FieldLabel>Study days per week: {profile.weekly_study_days}</FieldLabel>
            <input aria-label="Study days per week" type="range" min={1} max={7} value={profile.weekly_study_days} onChange={(event) => update("weekly_study_days", Number(event.target.value))} className="w-full accent-blue-600" />
            <FieldLabel>Minutes per study day</FieldLabel>
            <ChoiceGrid values={[...MINUTES]} selected={profile.daily_study_minutes} format={(value) => `${value} min`} onSelect={(value) => update("daily_study_minutes", value as UserProfile["daily_study_minutes"])} />
          </div>
        )}

        {step === 3 && (
          <div>
            <Heading icon={<Clock3 className="h-5 w-5" />} title="Choose your main focus" />
            <div className="grid gap-3 sm:grid-cols-2">
              {FOCUSES.map((focus) => <Choice key={focus} active={profile.primary_focus === focus} label={focus.charAt(0).toUpperCase() + focus.slice(1)} onClick={() => update("primary_focus", focus)} large />)}
            </div>
            <div className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
              Testora will create {profile.weekly_study_days} focused tasks per week, up to {profile.daily_study_minutes} minutes per study day, toward Band {profile.target_band.toFixed(1)}.
            </div>
          </div>
        )}

        <div className="mt-8 flex justify-between border-t border-slate-200 pt-5">
          <Button variant="secondary" disabled={step === 1 || saving} onClick={() => setStep((value) => value - 1)}><ArrowLeft className="h-4 w-4" /> Back</Button>
          {step < 3 ? <Button onClick={() => setStep((value) => value + 1)}>Continue <ArrowRight className="h-4 w-4" /></Button> : <Button disabled={saving} onClick={finish}>{saving ? "Saving..." : "Continue to diagnostic"} <ArrowRight className="h-4 w-4" /></Button>}
        </div>
      </Card>
    </div>
  );
}

function Heading({ icon, title }: { icon: React.ReactNode; title: string }) {
  return <h2 className="mb-6 flex items-center gap-2 text-xl font-bold text-slate-950"><span className="text-[var(--brand)]">{icon}</span>{title}</h2>;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <p className="mb-2 mt-6 text-sm font-semibold text-slate-700">{children}</p>;
}

function Choice({ active, label, onClick, large = false }: { active: boolean; label: string; onClick: () => void; large?: boolean }) {
  return <button type="button" aria-pressed={active} onClick={onClick} className={`${large ? "h-16" : "h-11"} rounded-xl border px-3 text-sm font-semibold capitalize transition ${active ? "border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"}`}>{label}</button>;
}

function ChoiceGrid({ values, selected, format, onSelect }: { values: number[]; selected: number; format: (value: number) => string; onSelect: (value: number) => void }) {
  return <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">{values.map((value) => <Choice key={value} active={selected === value} label={format(value)} onClick={() => onSelect(value)} />)}</div>;
}

function ErrorMessage({ message }: { message: string }) {
  return <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{message}</p>;
}
