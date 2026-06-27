"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarDays, Check, Clock3, RefreshCw, SkipForward } from "lucide-react";
import { api, type StudyPlan } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Button, Card, Skeleton } from "@/shared/ui";

export function StudyPlan() {
  const { token, ready } = useRequireAuth();
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [busy, setBusy] = useState<number | "recalculate" | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { if (token) api.getStudyPlan().then(setPlan).catch((err) => setError(err.message)); }, [token]);
  if (!ready || !token) return null;
  if (!plan) return error ? <ErrorMessage message={error} /> : <Skeleton className="h-96 w-full" />;

  const update = async (id: number, status: "completed" | "skipped") => {
    setBusy(id); setError("");
    try { await api.updateStudyPlanItem(id, status); setPlan(await api.getStudyPlan()); } catch (err) { setError(err instanceof Error ? err.message : "Could not update task"); } finally { setBusy(null); }
  };
  const recalculate = async () => {
    setBusy("recalculate"); setError("");
    try { setPlan(await api.recalculateStudyPlan()); } catch (err) { setError(err instanceof Error ? err.message : "Could not recalculate plan"); } finally { setBusy(null); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold text-[var(--brand)]">Personalized each week</p><h1 className="mt-1 text-3xl font-bold text-slate-950">Study plan</h1><p className="mt-2 text-slate-600">{formatDate(plan.week_start)} to {formatDate(plan.week_end)}</p></div><Button variant="secondary" disabled={busy !== null} onClick={recalculate}><RefreshCw className={`h-4 w-4 ${busy === "recalculate" ? "animate-spin" : ""}`} /> Recalculate</Button></div>
      {error && <ErrorMessage message={error} />}
      <Card className="p-5"><div className="flex items-center justify-between text-sm"><span className="font-semibold text-slate-800">Weekly progress</span><span className="text-slate-500">{plan.completed}/{plan.total} completed</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-emerald-500 transition-all" style={{ width: `${plan.progress}%` }} /></div></Card>
      {plan.items.length === 0 ? <Card className="p-8 text-center text-slate-500">No practice content is available for this week yet.</Card> : <div className="space-y-3">{plan.items.map((item) => <Card key={item.id} className={`p-5 ${item.status !== "pending" ? "bg-slate-50" : ""}`}><div className="flex flex-col gap-4 sm:flex-row sm:items-start"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-md px-2 py-1 text-xs font-semibold capitalize ${item.skill === "writing" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"}`}>{item.skill}</span><span className="flex items-center gap-1 text-xs text-slate-500"><CalendarDays className="h-3.5 w-3.5" />{formatDate(item.scheduled_date)}</span><span className="flex items-center gap-1 text-xs text-slate-500"><Clock3 className="h-3.5 w-3.5" />{item.minutes} min</span>{item.status !== "pending" && <span className="rounded-md bg-slate-200 px-2 py-1 text-xs font-semibold capitalize text-slate-600">{item.status}</span>}</div><h2 className="mt-2 text-lg font-bold text-slate-950">{item.title}</h2><p className="mt-1 text-sm leading-6 text-slate-600">{item.reason}</p></div><div className="flex shrink-0 flex-wrap gap-2">{item.status === "pending" && <><Link href={item.href} className="inline-flex h-10 items-center justify-center rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700">Start</Link><Button aria-label={`Complete ${item.title}`} variant="secondary" disabled={busy === item.id} onClick={() => update(item.id, "completed")}><Check className="h-4 w-4" /></Button><Button aria-label={`Skip ${item.title}`} variant="ghost" disabled={busy === item.id} onClick={() => update(item.id, "skipped")}><SkipForward className="h-4 w-4" /></Button></>}</div></div></Card>)}</div>}
    </div>
  );
}
function formatDate(value: string) { return new Date(`${value}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" }); }
function ErrorMessage({ message }: { message: string }) { return <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{message}</p>; }
