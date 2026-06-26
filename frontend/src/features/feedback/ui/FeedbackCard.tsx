import { CheckCircle2, AlertTriangle, ArrowRight, TrendingUp } from "lucide-react";
import { Feedback } from "@/shared/api";
import { Card } from "@/shared/ui";

function bandColor(band: number): string {
  if (band >= 7) return "text-green-600";
  if (band >= 5.5) return "text-amber-600";
  return "text-red-600";
}

function barColor(band: number): string {
  if (band >= 7) return "bg-green-500";
  if (band >= 5.5) return "bg-amber-500";
  return "bg-red-500";
}

export function FeedbackCard({ feedback }: { feedback: Feedback }) {
  const hasCriteria = Object.keys(feedback.criteria).length > 0;
  const graded = feedback.band > 0 || hasCriteria;
  const notes = feedback.criteria_notes ?? {};
  const strengths = feedback.strengths ?? [];
  const weaknesses = feedback.weaknesses ?? [];
  const actions =
    feedback.actions && feedback.actions.length > 0
      ? feedback.actions
      : feedback.suggestions;
  const roadmap = feedback.roadmap ?? [];

  return (
    <div className="space-y-6">
      {/* Overall band */}
      <Card className="overflow-hidden">
        <div className="bg-hero p-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Estimated IELTS band
          </p>
          {graded ? (
            <p className={`text-6xl font-extrabold ${bandColor(feedback.band)}`}>
              {feedback.band.toFixed(1)}
            </p>
          ) : (
            <p className="mt-2 text-2xl font-bold text-slate-400">Awaiting review</p>
          )}
        </div>
      </Card>

      {/* Per-criterion scores + examiner notes */}
      {hasCriteria && (
        <Card className="p-6">
          <h3 className="mb-4 font-semibold text-slate-900">By criterion</h3>
          <div className="space-y-4">
            {Object.entries(feedback.criteria).map(([name, band]) => (
              <div key={name}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-slate-700">{name}</span>
                  <span className="font-semibold text-slate-900">{band.toFixed(1)}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${barColor(band)}`}
                    style={{ width: `${(band / 9) * 100}%` }}
                  />
                </div>
                {notes[name] && (
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{notes[name]}</p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Summary */}
      <Card className="p-6">
        <h3 className="mb-2 font-semibold text-slate-900">Examiner summary</h3>
        <p className="text-sm leading-relaxed text-slate-600">{feedback.summary}</p>
      </Card>

      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {strengths.length > 0 && (
            <Card className="p-6">
              <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                Strengths
              </h3>
              <ul className="space-y-2">
                {strengths.map((s, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600">
                    <span className="mt-0.5 text-emerald-500">•</span>
                    {s}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {weaknesses.length > 0 && (
            <Card className="p-6">
              <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                Areas to improve
              </h3>
              <ul className="space-y-2">
                {weaknesses.map((w, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600">
                    <span className="mt-0.5 text-amber-500">•</span>
                    {w}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {actions.length > 0 && (
        <Card className="p-6">
          <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
            <ArrowRight className="h-5 w-5 text-blue-500" />
            What to do next
          </h3>
          <ul className="space-y-2">
            {actions.map((a, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-600">
                <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-blue-600">
                  {i + 1}
                </span>
                {a}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {roadmap.length > 0 && (
        <Card className="p-6">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-slate-900">
            <TrendingUp className="h-5 w-5 text-[var(--brand)]" />
            Your roadmap
          </h3>
          <div className="space-y-4">
            {roadmap.map((step, i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] p-4">
                <p className="mb-2 text-sm font-semibold text-slate-900">
                  To reach Band {step.target_band.toFixed(1)}
                </p>
                <ul className="space-y-1.5">
                  {step.actions.map((a, j) => (
                    <li key={j} className="flex gap-2 text-sm text-slate-600">
                      <span className="mt-0.5 text-[var(--brand)]">→</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
