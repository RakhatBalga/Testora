import type { Dispatch, SetStateAction } from "react";
import type { UserProfile } from "@/shared/api";
import { Button } from "@/shared/ui";

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

export function StudySettings({
  profile,
  setProfile,
  resettingPlan,
  savingSettings,
  onReset,
  onSave,
}: {
  profile: UserProfile;
  setProfile: Dispatch<SetStateAction<UserProfile | null>>;
  resettingPlan: boolean;
  savingSettings: boolean;
  onReset: () => void;
  onSave: () => void;
}) {
  return (
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:80ms]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><h2 className="font-semibold text-slate-900">Study settings</h2><p className="mt-1 text-sm text-slate-500">Used for your weekly plan.</p></div>
          <div className="flex flex-wrap gap-2"><Button variant="secondary" disabled={resettingPlan} onClick={onReset}>{resettingPlan ? "Resetting..." : "Reset plan"}</Button><Button disabled={savingSettings} onClick={onSave}>{savingSettings ? "Saving..." : "Save settings"}</Button></div>
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
            <span className="mt-1 block text-xs font-normal text-slate-500">Used to translate saved vocabulary.</span>
          </label>
        </div>
      </section>
  );
}
