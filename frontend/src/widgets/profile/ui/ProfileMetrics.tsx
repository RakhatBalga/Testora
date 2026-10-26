import { Skeleton } from "@/shared/ui";

export function ProfileMetrics({
  loading,
  totalSessions,
  avgBand,
  bestBand,
  aiReviews,
}: {
  loading: boolean;
  totalSessions: number;
  avgBand: number | null;
  bestBand: number | null;
  aiReviews: number;
}) {
  return (
      <section className="grid animate-fade-up grid-cols-2 gap-3 [animation-delay:100ms] sm:gap-4 lg:grid-cols-4">
        <ProfileMetric label="Sessions" value={loading ? null : String(totalSessions)} />
        <ProfileMetric
          label="Average band"
          value={loading ? null : avgBand === null ? "-" : avgBand.toFixed(1)}
        />
        <ProfileMetric
          label="Best band"
          value={loading ? null : bestBand === null ? "-" : bestBand.toFixed(1)}
        />
        <ProfileMetric label="AI reviews" value={loading ? null : String(aiReviews)} />
      </section>
  );
}

function ProfileMetric({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm shadow-slate-200/40 before:absolute before:inset-y-0 before:left-0 before:w-1 before:bg-[var(--brand)] sm:p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {label}
      </p>
      {value === null ? (
        <Skeleton className="mt-2 h-9 w-16 rounded-lg" />
      ) : (
        <p className="mt-1 text-2xl font-extrabold tracking-tight text-[var(--text-primary)] sm:text-3xl">
          {value}
        </p>
      )}
    </div>
  );
}
