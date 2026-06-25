import { Feedback } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { CheckCircle2, AlertTriangle, Target, TrendingUp } from "lucide-react";

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

      {/* Strengths + Weaknesses */}
      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="grid gap-4 lg:grid-cols-2">
          {strengths.length > 0 && (
            <Card className="p-6">
              <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
                <CheckCircle2 className="h-4 w-4 text-green-600" /> Strengths
              </h3>
              <ul className="space-y-2">
                {strengths.map((s, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600">
                    <span className="mt-0.5 text-green-500">•</span>
                    {s}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {weaknesses.length > 0 && (
            <Card className="p-6">
              <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
                <AlertTriangle className="h-4 w-4 text-amber-600" /> Weaknesses
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

      {/* Priority improvements */}
      {feedback.suggestions.length > 0 && (
        <Card className="p-6">
          <h3 className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
            <Target className="h-4 w-4 text-[var(--brand)]" /> Priority improvements
          </h3>
          <ol className="space-y-2.5">
            {feedback.suggestions.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-600">
                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[var(--brand)]/[0.1] text-xs font-bold text-[var(--brand)]">
                  {i + 1}
                </span>
                <span className="mt-0.5">{s}</span>
              </li>
            ))}
          </ol>
        </Card>
      )}

      {/* Band improvement roadmap */}
      {roadmap.length > 0 && (
        <Card className="p-6">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-slate-900">
            <TrendingUp className="h-4 w-4 text-[var(--brand)]" /> Your roadmap
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
