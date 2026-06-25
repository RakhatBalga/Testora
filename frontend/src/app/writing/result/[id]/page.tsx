"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, WritingSubmission, type ProgressImpact as ProgressImpactData } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { FeedbackCard } from "@/components/FeedbackCard";
import { ProgressImpact } from "@/components/dashboard/ProgressImpact";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { LinkButton } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

export default function WritingResultPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const submissionId = Number(params.id);

  const [submission, setSubmission] = useState<WritingSubmission | null>(null);
  const [impact, setImpact] = useState<ProgressImpactData | null>(null);
  const [impactLoading, setImpactLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api
      .getWritingSubmission(submissionId)
      .then(setSubmission)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    const impactTimer = window.setTimeout(() => {
      setImpactLoading(true);
      api
        .getProgressImpact("writing", submissionId)
        .then(setImpact)
        .catch(() => setImpact(null))
        .finally(() => setImpactLoading(false));
    }, 0);
    return () => window.clearTimeout(impactTimer);
  }, [token, submissionId]);

  if (!ready || !token) return null;
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-56 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  if (error) {
    return (
      <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
    );
  }
  if (!submission) return null;

  return (
    <div className="space-y-8">
      <Card className="overflow-hidden">
        <div className="bg-hero p-8 text-center">
          <Badge tone="blue" className="mb-3">
            Writing result
          </Badge>
          <h1 className="text-2xl font-bold text-slate-900">
            {submission.task_title}
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {new Date(submission.created_at).toLocaleString()} ·{" "}
            {submission.word_count} words · {submission.status}
          </p>
        </div>
      </Card>

      {submission.feedback ? (
        <FeedbackCard feedback={submission.feedback} />
      ) : (
        <Card className="p-6 text-center text-slate-500">
          Feedback is not available yet.
        </Card>
      )}

      {impactLoading ? <Skeleton className="h-48 w-full" /> : <ProgressImpact data={impact} />}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Prompt
          </h2>
          <p className="whitespace-pre-line leading-relaxed text-slate-700">
            {submission.task_prompt}
          </p>
        </Card>

        <Card className="p-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Your response
          </h2>
          <p className="whitespace-pre-line leading-relaxed text-slate-700">
            {submission.text}
          </p>
        </Card>
      </div>

      <div className="flex flex-wrap gap-3">
        <LinkButton href="/writing">Back to writing</LinkButton>
        <LinkButton href="/profile" variant="secondary">
          My results
        </LinkButton>
      </div>
    </div>
  );
}
