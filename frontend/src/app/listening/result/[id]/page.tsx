"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, Clock3, RotateCcw, XCircle } from "lucide-react";
import { api, type ListeningReview } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Button, Card, Skeleton } from "@/shared/ui";

function timestamp(seconds: number | null): string {
  if (seconds === null) return "";
  const value = Math.max(0, Math.floor(seconds));
  return `${Math.floor(value / 60)}:${(value % 60).toString().padStart(2, "0")}`;
}

export default function ListeningResultPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const router = useRouter();
  const attemptId = Number(params?.id);
  const [review, setReview] = useState<ListeningReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api.getListeningReview(attemptId)
      .then(setReview)
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Could not load result"))
      .finally(() => setLoading(false));
  }, [attemptId, token]);

  const sectionScores = useMemo(() => review?.sections.map((section) => {
    const answers = review.answers.filter((answer) => answer.section_order === section.order);
    return { ...section, correct: answers.filter((answer) => answer.is_correct).length, total: answers.length, answers };
  }) ?? [], [review]);

  if (!ready || !token) return null;
  if (loading) return <div className="space-y-4"><Skeleton className="h-44 w-full" /><Skeleton className="h-64 w-full" /></div>;
  if (error) return <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  if (!review) return <Card className="p-8 text-center text-slate-500">Listening result is unavailable.</Card>;

  const retake = () => {
    localStorage.removeItem(`listening-${review.test_id}-mode`);
    router.push(`/listening/${review.test_id}`);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-16">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-sm font-semibold uppercase text-teal-700">Listening result · {review.mode} mode</p><h1 className="mt-1 text-2xl font-extrabold text-slate-950">{review.test_title}</h1></div>
        <Button variant="secondary" onClick={retake}><RotateCcw className="h-4 w-4" /> Retake</Button>
      </div>

      <Card className="overflow-hidden">
        <div className="grid gap-px bg-slate-200 sm:grid-cols-3">
          <div className="bg-white p-6 text-center"><p className="text-xs font-semibold uppercase text-slate-400">Score</p><p className="mt-1 text-4xl font-extrabold text-slate-950">{review.score}<span className="text-2xl text-slate-300">/{review.total}</span></p></div>
          <div className="bg-white p-6 text-center"><p className="text-xs font-semibold uppercase text-slate-400">Estimated band</p><p className="mt-1 text-4xl font-extrabold text-teal-700">{review.band?.toFixed(1) ?? "-"}</p></div>
          <div className="bg-white p-6 text-center"><p className="text-xs font-semibold uppercase text-slate-400">Accuracy</p><p className="mt-1 text-4xl font-extrabold text-slate-950">{review.accuracy}%</p></div>
        </div>
      </Card>

      <section>
        <h2 className="text-lg font-bold text-slate-950">Section breakdown</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {sectionScores.map((section) => <div key={section.id} className="rounded-lg border border-slate-200 bg-white p-4"><p className="text-xs font-semibold uppercase text-slate-400">Section {section.order}</p><p className="mt-1 text-2xl font-bold text-slate-950">{section.correct}/{section.total}</p></div>)}
        </div>
      </section>

      {sectionScores.map((section) => (
        <section key={section.id} className="space-y-3">
          <div className="flex items-baseline justify-between gap-3"><h2 className="text-lg font-bold text-slate-950">{section.title}</h2><span className="text-sm font-semibold text-slate-500">{section.correct}/{section.total}</span></div>
          {section.answers.map((answer) => (
            <Card key={answer.question_id} className={`border-l-4 p-4 ${answer.is_correct ? "border-l-emerald-500" : "border-l-red-500"}`}>
              <div className="flex gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate-100 text-sm font-bold text-slate-700">{answer.order}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3"><p className="font-medium text-slate-950">{answer.text}</p>{answer.is_correct ? <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" /> : <XCircle className="h-5 w-5 shrink-0 text-red-600" />}</div>
                  <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><p className={`rounded-md px-3 py-2 ${answer.is_correct ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`}>Your answer: <strong>{answer.user_answer || "No answer"}</strong></p><p className="rounded-md bg-slate-50 px-3 py-2 text-slate-700">Correct: <strong>{answer.correct_answer}</strong></p></div>
                  {answer.target_skill && <p className="mt-3 text-xs font-semibold uppercase text-teal-700">Skill: {answer.target_skill.replaceAll("_", " ")}</p>}
                  {answer.explanation && <p className="mt-2 text-sm leading-6 text-slate-600">{answer.explanation}</p>}
                  {answer.evidence.length > 0 && <div className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950"><p className="flex items-center gap-1.5 text-xs font-semibold uppercase text-amber-800"><Clock3 className="h-3.5 w-3.5" /> Evidence {answer.evidence.map((item) => timestamp(item.start)).filter(Boolean).join(" · ")}</p><p className="mt-1">{answer.evidence.map((item) => item.quote).join(" ")}</p></div>}
                </div>
              </div>
            </Card>
          ))}
          <details className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <summary className="cursor-pointer text-sm font-semibold text-slate-800">Section transcript</summary>
            <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
              {section.transcript_segments.map((segment) => <div key={segment.id} className="grid gap-1 text-sm sm:grid-cols-[72px_100px_1fr]"><span className="tabular-nums text-slate-400">{timestamp(segment.start)}</span><strong className="text-slate-700">{segment.speaker}</strong><p className="leading-6 text-slate-600">{segment.text}</p></div>)}
            </div>
          </details>
        </section>
      ))}
    </div>
  );
}
