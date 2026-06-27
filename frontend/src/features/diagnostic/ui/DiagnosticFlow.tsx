"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, CheckCircle2, PenLine, RefreshCw } from "lucide-react";
import { api, type DiagnosticState } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Button, Card, LinkButton, Skeleton } from "@/shared/ui";

export function DiagnosticFlow() {
  const { token, ready } = useRequireAuth();
  const [state, setState] = useState<DiagnosticState | null>(null);
  const [selected, setSelected] = useState<("writing" | "reading")[]>(["writing", "reading"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (token) api.getDiagnostic().then(setState).catch((err) => setError(err.message));
  }, [token]);
  if (!ready || !token) return null;
  if (!state) return error ? <Message message={error} /> : <Skeleton className="h-96 w-full" />;

  const run = async (action: () => Promise<DiagnosticState>) => {
    setBusy(true); setError("");
    try { setState(await action()); } catch (err) { setError(err instanceof Error ? err.message : "Diagnostic update failed"); } finally { setBusy(false); }
  };
  const toggle = (skill: "writing" | "reading") => setSelected((value) => value.includes(skill) ? value.filter((item) => item !== skill) : [...value, skill]);
  const doneWriting = !!state.writing_submission_id;
  const doneReading = !!state.reading_attempt_id;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div><p className="text-sm font-semibold text-[var(--brand)]">Personalized baseline</p><h1 className="mt-1 text-3xl font-bold text-slate-950">Quick diagnostic</h1><p className="mt-2 text-slate-600">Use one or both skills. This is an approximate practice estimate, not an official IELTS score, and your level changes only after you confirm it.</p></div>
      {error && <Message message={error} />}

      {state.status === "not_started" || state.status === "skipped" ? (
        <Card className="p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <SkillChoice icon={<PenLine className="h-5 w-5" />} title="Writing" detail="Criterion-level feedback" active={selected.includes("writing")} onClick={() => toggle("writing")} />
            <SkillChoice icon={<BookOpen className="h-5 w-5" />} title="Reading" detail="Question-type accuracy" active={selected.includes("reading")} onClick={() => toggle("reading")} />
          </div>
          <div className="mt-6 flex flex-wrap gap-3"><Button disabled={busy || selected.length === 0} onClick={() => run(() => api.startDiagnostic(selected))}>Start diagnostic</Button><Button variant="ghost" disabled={busy} onClick={() => run(api.skipDiagnostic)}>Skip for now</Button></div>
        </Card>
      ) : (
        <Card className="p-6">
          <div className="flex items-center justify-between gap-4"><h2 className="text-lg font-bold text-slate-950">Diagnostic progress</h2><span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold capitalize text-blue-700">{state.status.replace("_", " ")}</span></div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {state.skills.includes("writing") && <DiagnosticTask title="Writing" done={doneWriting} href={state.writing_task_id ? `/writing/${state.writing_task_id}` : null} />}
            {state.skills.includes("reading") && <DiagnosticTask title="Reading" done={doneReading} href={state.reading_test_id ? `/reading/${state.reading_test_id}` : null} />}
          </div>
          {state.status === "in_progress" && <div className="mt-6 flex flex-wrap gap-3"><Button disabled={busy} onClick={() => run(api.refreshDiagnostic)}><RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} /> Check progress</Button><Button variant="ghost" disabled={busy} onClick={() => run(api.skipDiagnostic)}>Skip diagnostic</Button></div>}
          {state.status === "completed" && state.provisional_level !== null && <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-5"><p className="text-sm font-semibold text-emerald-800">Provisional level</p><p className="mt-1 text-4xl font-extrabold text-emerald-700">{state.provisional_level.toFixed(1)}</p><p className="mt-2 text-sm text-emerald-800">Update your current level to this diagnostic estimate?</p><div className="mt-4 flex gap-3"><Button disabled={busy} onClick={() => run(api.acceptDiagnosticLevel)}>Use this level</Button><LinkButton href="/study-plan" variant="secondary">Keep current level</LinkButton></div></div>}
        </Card>
      )}
      <Link href="/" className="inline-flex text-sm font-semibold text-[var(--brand)] hover:underline">Back to dashboard</Link>
    </div>
  );
}

function SkillChoice({ icon, title, detail, active, onClick }: { icon: React.ReactNode; title: string; detail: string; active: boolean; onClick: () => void }) {
  return <button type="button" aria-pressed={active} onClick={onClick} className={`flex items-center gap-3 rounded-xl border p-5 text-left transition ${active ? "border-blue-600 bg-blue-50 ring-1 ring-blue-600" : "border-slate-200 hover:border-slate-300"}`}><span className={active ? "text-blue-700" : "text-slate-400"}>{icon}</span><span><strong className="block text-slate-950">{title}</strong><span className="text-sm text-slate-500">{detail}</span></span></button>;
}
function DiagnosticTask({ title, done, href }: { title: string; done: boolean; href: string | null }) {
  return <div className="flex items-center justify-between rounded-xl border border-slate-200 p-4"><div className="flex items-center gap-2">{done ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <span className="h-5 w-5 rounded-full border-2 border-slate-300" />}<span className="font-semibold text-slate-800">{title}</span></div>{done ? <span className="text-sm text-emerald-700">Completed</span> : href ? <LinkButton href={href} size="sm">Open task</LinkButton> : <span className="text-sm text-slate-400">Unavailable</span>}</div>;
}
function Message({ message }: { message: string }) { return <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{message}</p>; }
