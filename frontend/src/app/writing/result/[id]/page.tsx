"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, RefreshCw } from "lucide-react";
import {
  api,
  type WritingSubmission,
} from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { FeedbackCard, EssayComparison } from "@/features/feedback";
import { Badge } from "@/shared/ui";
import { Button, Card } from "@/shared/ui";
import { LinkButton } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

export default function WritingResultPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const submissionId = Number(params?.id);

  const [submission, setSubmission] = useState<WritingSubmission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState("");

  useEffect(() => {
    if (!token) return;
    api
      .getWritingSubmission(submissionId)
      .then(setSubmission)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, submissionId]);

  const handleRetry = async () => {
    if (!submission || retrying) return;
    setRetrying(true);
    setRetryError("");
    try {
      const updated = await api.retryWritingSubmission(submission.id);
      setSubmission(updated);
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setRetrying(false);
    }
  };

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
  const isFailed = submission.status === "failed";

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

      {isFailed ? (
        <Card className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
                <AlertTriangle className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-semibold text-slate-900">Review failed, try again</h2>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">
                  {submission.feedback?.summary ||
                    "Automatic grading could not be completed for this response."}
                </p>
                {retryError && (
                  <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
                    {retryError}
                  </p>
                )}
              </div>
            </div>
            <Button onClick={handleRetry} disabled={retrying} className="shrink-0">
              <RefreshCw className={`h-4 w-4 ${retrying ? "animate-spin" : ""}`} />
              {retrying ? "Retrying" : "Retry review"}
            </Button>
          </div>
        </Card>
      ) : submission.feedback ? (
        <FeedbackCard feedback={submission.feedback} currentBand={submission.band} />
      ) : (
        <Card className="p-6 text-center text-slate-500">
          Feedback is not available yet.
        </Card>
      )}

      <EssayComparison
        prompt={submission.task_prompt}
        response={submission.text}
        improved={submission.improved_text}
      />

      <div className="flex flex-wrap gap-3">
        <LinkButton href="/writing">Back to writing</LinkButton>
        <LinkButton href="/profile" variant="secondary">
          My results
        </LinkButton>
      </div>
    </div>
  );
}
