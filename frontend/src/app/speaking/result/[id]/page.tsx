"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, authedMediaUrl, SpeakingSubmission } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { FeedbackCard } from "@/features/feedback";
import { Badge } from "@/shared/ui";
import { Card } from "@/shared/ui";
import { LinkButton } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

export default function SpeakingResultPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const submissionId = Number(params?.id);

  const [submission, setSubmission] = useState<SpeakingSubmission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api
      .getSpeakingSubmission(submissionId)
      .then(setSubmission)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
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

  const audioSrc = authedMediaUrl(submission.audio_url);

  return (
    <div className="space-y-8">
      <Card className="overflow-hidden">
        <div className="bg-hero p-8 text-center">
          <Badge tone="green" className="mb-3">
            Speaking result
          </Badge>
          <h1 className="text-2xl font-bold text-slate-900">
            Speaking Part {submission.task_part}
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {new Date(submission.created_at).toLocaleString()}
          </p>
          {audioSrc && (
            <audio controls src={audioSrc} className="mx-auto mt-6 w-full max-w-xl">
              Your browser does not support audio.
            </audio>
          )}
        </div>
      </Card>

      {submission.feedback ? (
        <FeedbackCard feedback={submission.feedback} />
      ) : (
        <Card className="p-6 text-center text-slate-500">
          Feedback is not available yet.
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Questions
          </h2>
          <div className="space-y-3">
            {submission.questions.map((question, index) => (
              <p key={question} className="flex gap-3 text-slate-700">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-700">
                  {index + 1}
                </span>
                <span>{question}</span>
              </p>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Transcript
          </h2>
          {submission.transcript ? (
            <p className="whitespace-pre-line leading-relaxed text-slate-700">
              {submission.transcript}
            </p>
          ) : (
            <p className="text-slate-500">
              Transcript is not available yet. Whisper or another speech-to-text
              provider can be connected later.
            </p>
          )}
        </Card>
      </div>

      <div className="flex flex-wrap gap-3">
        <LinkButton href="/speaking">Back to speaking</LinkButton>
        <LinkButton href="/profile" variant="secondary">
          My results
        </LinkButton>
      </div>
    </div>
  );
}
