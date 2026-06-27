"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  CalendarClock,
  Check,
  ClipboardCheck,
  NotebookTabs,
  PenLine,
  Target,
} from "lucide-react";
import { api, type LearningDashboard } from "@/shared/api";
import { Card, Skeleton } from "@/shared/ui";
import { formatDisplayName, greeting } from "@/shared/lib";

export function CoachDashboard({ username }: { username: string | null }) {
  const [data, setData] = useState<LearningDashboard | null>(null);
  const [error, setError] = useState("");
  const [completing, setCompleting] = useState(false);

  const load = () => api.getLearningDashboard().then(setData).catch((err) => setError(err.message));
  useEffect(() => { void load(); }, []);

  if (!data) {
    return error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : <div className="space-y-4"><Skeleton className="h-44 w-full" /><Skeleton className="h-64 w-full" /></div>;
  }

  const current = data.profile.current_level;
  const today = data.today;
  const completeToday = async () => {
    if (!today) return;
    setCompleting(true);
    try { await api.updateStudyPlanItem(today.id, "completed"); await load(); } finally { setCompleting(false); }
  };

  return (
    <div className="space-y-6">
      {!data.profile.onboarding_completed && (
        <section className="flex flex-col gap-4 rounded-xl border border-blue-200 bg-blue-50 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="font-semibold text-blue-950">Personalize your plan</p><p className="mt-1 text-sm text-blue-800">Set your schedule and focus. Your existing practice remains available.</p></div>
          <Link href="/onboarding" className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700">Set up profile <ArrowRight className="h-4 w-4" /></Link>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div><p className="text-sm font-semibold text-[var(--brand)]">Dashboard</p><h1 className="mt-1 text-3xl font-bold text-slate-950">{greeting()}, {formatDisplayName(username)}</h1><p className="mt-2 text-slate-600">Your next step is based on completed Writing and Reading work.</p></div>
          <Link href="/study-plan" className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"><CalendarClock className="h-4 w-4" /> Weekly plan</Link>
        </div>
        <div className="mt-6 grid gap-4 border-t border-slate-200 pt-5 sm:grid-cols-3">
          <Metric label="Target band" value={data.profile.target_band.toFixed(1)} hint="your goal" icon={<Target className="h-4 w-4" />} />
          <Metric label="Current level" value={current === null ? "Not set" : current.toFixed(1)} hint={data.profile.current_level_source || "complete a diagnostic"} icon={<ClipboardCheck className="h-4 w-4" />} />
          <Metric label="Exam countdown" value={data.profile.days_to_exam === null ? "No date" : `${data.profile.days_to_exam} days`} hint={data.profile.exam_date ? new Date(`${data.profile.exam_date}T12:00:00`).toLocaleDateString() : "set in profile"} icon={<CalendarClock className="h-4 w-4" />} />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.65fr)]">
        <Card className="p-6">
          <div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase text-slate-400">Today</p><h2 className="mt-1 text-xl font-bold text-slate-950">{today?.title || "You are caught up"}</h2></div>{today && <span className={`rounded-md px-2 py-1 text-xs font-semibold capitalize ${today.skill === "writing" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"}`}>{today.skill}</span>}</div>
          {today ? <><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">{today.reason}</p><p className="mt-3 text-sm font-medium text-slate-500">{today.minutes} minutes</p><div className="mt-5 flex flex-wrap gap-3"><Link href={today.href} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700">Start task <ArrowRight className="h-4 w-4" /></Link><button type="button" disabled={completing} onClick={completeToday} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"><Check className="h-4 w-4" /> Mark complete</button></div></> : <p className="mt-3 text-sm text-slate-500">Recalculate your plan when you are ready for the next task.</p>}
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between"><h2 className="font-bold text-slate-950">This week</h2><span className="text-sm font-semibold text-emerald-700">{data.weekly_plan.completed}/{data.weekly_plan.total}</span></div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-emerald-500" style={{ width: `${data.weekly_plan.progress}%` }} /></div>
          <div className="mt-5 space-y-2">{data.weekly_plan.items.slice(0, 4).map((item) => <div key={item.id} className="flex items-center gap-2 text-sm"><span className={`h-2 w-2 rounded-full ${item.status === "completed" ? "bg-emerald-500" : item.status === "skipped" ? "bg-slate-300" : "bg-blue-500"}`} /><span className={item.status === "completed" ? "text-slate-400 line-through" : "text-slate-600"}>{item.title}</span></div>)}</div>
          <Link href="/study-plan" className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-[var(--brand)] hover:underline">Open full plan <ArrowRight className="h-3.5 w-3.5" /></Link>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <WeaknessCard icon={<PenLine className="h-5 w-5" />} title="Writing focus" weakness={data.weaknesses.writing} empty="Complete a Writing task to find your limiting criterion." suffix="Band" />
        <WeaknessCard icon={<BookOpen className="h-5 w-5" />} title="Reading focus" weakness={data.weaknesses.reading} empty="Complete a Reading test to find your weakest question type." suffix="accuracy" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6"><div className="flex items-center justify-between"><div className="flex items-center gap-2"><NotebookTabs className="h-5 w-5 text-[var(--brand)]" /><h2 className="font-bold text-slate-950">Mistake notebook</h2></div><span className="text-sm font-semibold text-slate-500">{data.mistakes.total} total</span></div><div className="mt-5 grid grid-cols-3 gap-3 text-center"><MiniMetric label="New" value={data.mistakes.new} /><MiniMetric label="Reviewing" value={data.mistakes.reviewing} /><MiniMetric label="Mastered" value={data.mistakes.mastered} /></div><Link href="/mistakes" className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-[var(--brand)] hover:underline">Review mistakes <ArrowRight className="h-3.5 w-3.5" /></Link></Card>
        <Card className="p-6"><div className="flex items-center justify-between"><h2 className="font-bold text-slate-950">Recent practice</h2><Link href="/history" className="text-sm font-semibold text-[var(--brand)] hover:underline">History</Link></div>{data.recent.length ? <div className="mt-4 space-y-3">{data.recent.map((item) => <Link key={item.id} href={item.href} className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 hover:bg-slate-50"><span><span className="block text-sm font-semibold text-slate-800">{item.title}</span><span className="text-xs capitalize text-slate-500">{item.skill}</span></span><span className="font-bold text-slate-900">{item.band?.toFixed(1) ?? "-"}</span></Link>)}</div> : <p className="mt-4 text-sm text-slate-500">Your first Writing or Reading result will appear here.</p>}</Card>
      </div>

      {data.diagnostic.status === "not_started" && <section className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-semibold text-slate-900">Not sure about your current level?</p><p className="mt-1 text-sm text-slate-500">Run a Writing and/or Reading diagnostic, then choose whether to update it.</p></div><Link href="/diagnostic" className="inline-flex h-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50">Open diagnostic</Link></section>}
    </div>
  );
}

function Metric({ label, value, hint, icon }: { label: string; value: string; hint: string; icon: React.ReactNode }) { return <div><p className="flex items-center gap-1.5 text-sm font-medium text-slate-500">{icon}{label}</p><p className="mt-1 text-2xl font-extrabold text-slate-950">{value}</p><p className="mt-0.5 text-xs text-slate-400">{hint}</p></div>; }
function MiniMetric({ label, value }: { label: string; value: number }) { return <div className="rounded-xl bg-slate-50 p-3"><p className="text-xl font-bold text-slate-900">{value}</p><p className="text-xs text-slate-500">{label}</p></div>; }
function WeaknessCard({ icon, title, weakness, empty, suffix }: { icon: React.ReactNode; title: string; weakness: { label: string; value: number; href: string } | null; empty: string; suffix: string }) { return <Card className="p-6"><div className="flex items-center gap-2 text-[var(--brand)]">{icon}<h2 className="font-bold text-slate-950">{title}</h2></div>{weakness ? <><p className="mt-4 text-lg font-bold text-slate-900">{weakness.label}</p><p className="mt-1 text-sm text-slate-500">{suffix === "Band" ? `Band ${weakness.value.toFixed(1)}` : `${weakness.value.toFixed(0)}% ${suffix}`}</p><Link href={weakness.href} className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[var(--brand)] hover:underline">Review evidence <ArrowRight className="h-3.5 w-3.5" /></Link></> : <p className="mt-4 text-sm leading-6 text-slate-500">{empty}</p>}</Card>; }
