"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowRight, RefreshCw, Target } from "lucide-react";
import {
  api,
  type WritingSubmission,
  type ProgressImpact as ProgressImpactData,
  type UserProfile,
} from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { FeedbackCard, EssayComparison } from "@/features/feedback";
import { ProgressImpact } from "@/features/progress-impact";
import { Badge } from "@/shared/ui";
import { Button, Card } from "@/shared/ui";
import { LinkButton } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

export default function WritingResultPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const submissionId = Number(params?.id);

  const [submission, setSubmission] = useState<WritingSubmission | null>(null);
  const [impact, setImpact] = useState<ProgressImpactData | null>(null);
  const [impactLoading, setImpactLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState("");
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .getWritingSubmission(submissionId)
      .then(setSubmission)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    api.getProfile().then(setProfile).catch(() => setProfile(null));
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

  const handleRetry = async () => {
    if (!submission || retrying) return;
    setRetrying(true);
    setRetryError("");
    try {
      const updated = await api.retryWritingSubmission(submission.id);
      setSubmission(updated);
      if (updated.status === "graded" && updated.band !== null) {
        setImpactLoading(true);
        try {
          setImpact(await api.getProgressImpact("writing", updated.id));
        } catch {
          setImpact(null);
        } finally {
          setImpactLoading(false);
        }
      } else {
        setImpact(null);
        setImpactLoading(false);
      }
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
  const scoredCriteria = Object.entries(submission.feedback?.criteria ?? {}).filter((entry): entry is [string, number] => typeof entry[1] === "number" && entry[1] > 0);
  const limitingCriterion = scoredCriteria.sort((a, b) => a[1] - b[1])[0];
  const gapToTarget = submission.band !== null && profile ? Math.max(0, profile.target_band - submission.band) : null;

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

      {!isFailed && submission.band !== null && profile && (
        <Card className="p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Target className="h-5 w-5 text-[var(--brand)]" /> Path to your target</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                You are {gapToTarget === 0 ? "at or above" : `${gapToTarget?.toFixed(1)} band${gapToTarget === 1 ? "" : "s"} below`} your target of {profile.target_band.toFixed(1)}.
                {limitingCriterion ? ` ${limitingCriterion[0]} is currently the lowest criterion at Band ${limitingCriterion[1].toFixed(1)}.` : ""}
              </p>
            </div>
            <LinkButton href={`/writing/${submission.task_id}`}>Practice again <ArrowRight className="h-4 w-4" /></LinkButton>
          </div>
          <LinkButton href="/mistakes?skill=writing" variant="secondary" className="mt-4">Review inline issues</LinkButton>
        </Card>
      )}

      {!isFailed &&
        (impactLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : (
          <ProgressImpact data={impact} />
        ))}

      <EssayComparison prompt={submission.task_prompt} response={submission.text} />

      <div className="flex flex-wrap gap-3">
        <LinkButton href="/writing">Back to writing</LinkButton>
        <LinkButton href="/profile" variant="secondary">
          My results
        </LinkButton>
      </div>
    </div>
  );
}
