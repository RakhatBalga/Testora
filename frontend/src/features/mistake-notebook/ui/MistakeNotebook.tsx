"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, BookOpen, CheckCircle2, PenLine } from "lucide-react";
import { api, type NotebookItem, type NotebookPage } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Button, Card, Skeleton } from "@/shared/ui";

type SkillFilter = "all" | "writing" | "reading";
type StatusFilter = "all" | "new" | "reviewing" | "mastered";

export function MistakeNotebook() {
  const { token, ready } = useRequireAuth();
  const [data, setData] = useState<NotebookPage | null>(null);
  const [skill, setSkill] = useState<SkillFilter>("all");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try { setData(await api.getMistakes({ skill: skill === "all" ? undefined : skill, status: status === "all" ? undefined : status, page, page_size: 12 })); } catch (err) { setError(err instanceof Error ? err.message : "Could not load mistakes"); }
  }, [skill, status, page]);
  useEffect(() => {
    if (!token) return;
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [token, load]);
  if (!ready || !token) return null;

  const setReviewStatus = async (item: NotebookItem, next: "new" | "reviewing" | "mastered") => {
    setBusy(item.id);
    try { await api.updateMistakeStatus(item.skill, item.source_id, next); await load(); } catch (err) { setError(err instanceof Error ? err.message : "Could not update mistake"); } finally { setBusy(null); }
  };

  return (
    <div className="space-y-6">
      <div><p className="text-sm font-semibold text-[var(--brand)]">Review and resolve</p><h1 className="mt-1 text-3xl font-bold text-slate-950">Mistake notebook</h1><p className="mt-2 text-slate-600">Writing feedback and incorrect Reading answers in one place.</p></div>
      {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <div className="flex flex-wrap justify-between gap-3"><Filter values={["all", "writing", "reading"]} selected={skill} onChange={(value) => { setSkill(value as SkillFilter); setPage(1); }} /><Filter values={["all", "new", "reviewing", "mastered"]} selected={status} onChange={(value) => { setStatus(value as StatusFilter); setPage(1); }} /></div>
      {!data ? <div className="space-y-3"><Skeleton className="h-40 w-full" /><Skeleton className="h-40 w-full" /></div> : data.items.length === 0 ? <Card className="p-10 text-center"><CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500" /><p className="mt-3 font-semibold text-slate-800">Nothing to review here</p><p className="mt-1 text-sm text-slate-500">Complete Writing or Reading practice to add evidence.</p></Card> : <div className="space-y-3">{data.items.map((item) => <Card key={item.id} className="p-5"><div className="flex flex-col gap-4 sm:flex-row"><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${item.skill === "writing" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"}`}>{item.skill === "writing" ? <PenLine className="h-5 w-5" /> : <BookOpen className="h-5 w-5" />}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="text-xs font-semibold uppercase text-slate-400">{item.label}</span><span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize text-slate-600">{item.status}</span></div>{item.quote && <blockquote className="mt-3 border-l-2 border-blue-300 pl-3 text-sm italic text-slate-700">“{item.quote}”</blockquote>}{item.skill === "reading" && <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><p className="rounded-lg bg-red-50 px-3 py-2 text-red-800">Your answer: <strong>{item.user_answer || "No answer"}</strong></p><p className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-800">Correct: <strong>{item.correct_answer}</strong></p></div>}{item.correct_answer && item.skill === "writing" && <p className="mt-3 text-sm text-slate-700">Try: <strong>{item.correct_answer}</strong></p>}{item.explanation && <p className="mt-2 text-sm leading-6 text-slate-600">{item.explanation}</p>}{item.evidence?.length ? <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">Evidence: {item.evidence.map((span) => span.text).join(" · ")}</div> : null}<div className="mt-4 flex flex-wrap items-center gap-2"><Link href={item.source_href} className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--brand)] hover:underline">{item.source_title}<ArrowUpRight className="h-3.5 w-3.5" /></Link><span className="flex-1" />{item.status !== "reviewing" && <Button size="sm" variant="secondary" disabled={busy === item.id} onClick={() => setReviewStatus(item, "reviewing")}>Reviewing</Button>}{item.status !== "mastered" ? <Button size="sm" disabled={busy === item.id} onClick={() => setReviewStatus(item, "mastered")}><CheckCircle2 className="h-4 w-4" /> Mastered</Button> : <Button size="sm" variant="secondary" disabled={busy === item.id} onClick={() => setReviewStatus(item, "new")}>Reopen</Button>}</div></div></div></Card>)}</div>}
      {data && data.total > data.page_size && <div className="flex items-center justify-center gap-3"><Button variant="secondary" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="text-sm text-slate-500">Page {page} of {Math.ceil(data.total / data.page_size)}</span><Button variant="secondary" disabled={page * data.page_size >= data.total} onClick={() => setPage((value) => value + 1)}>Next</Button></div>}
    </div>
  );
}

function Filter({ values, selected, onChange }: { values: string[]; selected: string; onChange: (value: string) => void }) { return <div className="flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1">{values.map((value) => <button key={value} type="button" onClick={() => onChange(value)} className={`rounded-lg px-3 py-1.5 text-sm font-semibold capitalize ${selected === value ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50"}`}>{value}</button>)}</div>; }
