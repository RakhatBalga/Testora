import { CheckCircle2, XCircle, RotateCcw } from "lucide-react";
import type { AttemptResult } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { rangeLabel, type ReadingGroup } from "./types";

type Props = {
  result: AttemptResult;
  groups: ReadingGroup[];
  onRetake: () => void;
};

function bandColor(band: number): string {
  if (band >= 7) return "text-green-600";
  if (band >= 5.5) return "text-amber-600";
  return "text-red-600";
}

export function ReadingReview({ result, groups, onRetake }: Props) {
  const byId = new Map(result.answers.map((a) => [a.question_id, a]));

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-16">
      {/* Score summary */}
      <Card className="overflow-hidden">
        <div className="grid gap-px bg-[var(--border)] sm:grid-cols-3">
          <div className="bg-white p-6 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Score</p>
            <p className="mt-1 text-4xl font-extrabold text-slate-900">
              {result.correct}
              <span className="text-2xl text-slate-300">/{result.total}</span>
            </p>
          </div>
          <div className="bg-white p-6 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Estimated band
            </p>
            <p className={`mt-1 text-4xl font-extrabold ${bandColor(result.band ?? 0)}`}>
              {result.band !== null ? result.band.toFixed(1) : "—"}
            </p>
          </div>
          <div className="bg-white p-6 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Accuracy</p>
            <p className="mt-1 text-4xl font-extrabold text-slate-900">{result.accuracy}%</p>
          </div>
        </div>
      </Card>

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">Answer review</h2>
        <Button variant="secondary" size="sm" onClick={onRetake}>
          <RotateCcw className="h-4 w-4" /> Retake
        </Button>
      </div>

      {/* Per-question review grouped by passage */}
      {groups.map((g) => (
        <div key={g.section.id} className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {rangeLabel(g.start, g.end)}
          </p>
          {g.questions.map((q) => {
            const a = byId.get(q.id);
            if (!a) return null;
            const correct = a.is_correct;
            return (
              <Card
                key={q.id}
                className={`border-l-4 p-4 ${
                  correct ? "border-l-green-500" : "border-l-red-500"
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm font-bold text-slate-600">
                    {q.number}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium leading-snug text-slate-900">{a.text}</p>

                    <div className="mt-3 space-y-1.5 text-sm">
                      <div className="flex items-start gap-2">
                        {correct ? (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600" />
                        ) : (
                          <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-600" />
                        )}
                        <span className={correct ? "text-green-700" : "text-red-700"}>
                          Your answer:{" "}
                          <strong>{a.user_answer?.trim() ? a.user_answer : "—"}</strong>
                        </span>
                      </div>
                      {!correct && (
                        <div className="flex items-start gap-2 pl-6 text-slate-600">
                          Correct answer: <strong className="text-slate-900">{a.correct_answer}</strong>
                        </div>
                      )}
                    </div>

                    {a.explanation && (
                      <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-600">
                        {a.explanation}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ))}
    </div>
  );
}
