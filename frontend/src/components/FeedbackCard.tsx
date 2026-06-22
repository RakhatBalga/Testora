import { Feedback } from "@/lib/api";
import { Card } from "@/components/ui/Card";

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

  return (
    <div className="space-y-6">
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

      {hasCriteria && (
        <Card className="p-6">
          <h3 className="mb-4 font-semibold text-slate-900">By criterion</h3>
          <div className="space-y-4">
            {Object.entries(feedback.criteria).map(([name, band]) => (
              <div key={name}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-slate-700">{name}</span>
                  <span className="font-semibold text-slate-900">
                    {band.toFixed(1)}
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${barColor(band)}`}
                    style={{ width: `${(band / 9) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-6">
        <h3 className="mb-2 font-semibold text-slate-900">Summary</h3>
        <p className="text-sm leading-relaxed text-slate-600">{feedback.summary}</p>
        {feedback.suggestions.length > 0 && (
          <>
            <h3 className="mb-2 mt-5 font-semibold text-slate-900">Suggestions</h3>
            <ul className="space-y-2">
              {feedback.suggestions.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-600">
                  <span className="mt-0.5 text-blue-500">•</span>
                  {s}
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>
    </div>
  );
}
