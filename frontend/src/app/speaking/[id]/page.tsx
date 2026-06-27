"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, Mic, RotateCcw, Square } from "lucide-react";
import { api, SpeakingTask } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Badge } from "@/shared/ui";
import { Button } from "@/shared/ui";
import { Card } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

type Phase = "prep" | "ready" | "recording" | "recorded";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function preferredMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
  return types.find((type) => MediaRecorder.isTypeSupported(type));
}

function partTone(part: number) {
  if (part === 1) return "blue";
  if (part === 2) return "violet";
  return "green";
}

export default function SpeakingTaskPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const router = useRouter();
  const taskId = Number(params?.id);

  const [task, setTask] = useState<SpeakingTask | null>(null);
  const [phase, setPhase] = useState<Phase>("prep");
  const [prepLeft, setPrepLeft] = useState(0);
  const [speakLeft, setSpeakLeft] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const cleanupStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
  }, []);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
      return;
    }
    cleanupStream();
  }, [cleanupStream]);

  useEffect(() => {
    if (!token) return;
    api
      .getSpeakingTask(taskId)
      .then((data) => {
        setTask(data);
        setPrepLeft(data.prep_seconds);
        setSpeakLeft(data.speak_seconds);
        setPhase(data.prep_seconds > 0 ? "prep" : "ready");
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, taskId]);

  useEffect(() => {
    if (phase !== "prep" || prepLeft <= 0) return;
    const timer = setTimeout(() => {
      if (prepLeft <= 1) {
        setPrepLeft(0);
        setPhase("ready");
      } else {
        setPrepLeft(prepLeft - 1);
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [phase, prepLeft]);

  useEffect(() => {
    if (phase !== "recording" || speakLeft <= 0) return;
    const timer = setTimeout(() => {
      if (speakLeft <= 1) {
        setSpeakLeft(0);
        stopRecording();
      } else {
        setSpeakLeft(speakLeft - 1);
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [phase, speakLeft, stopRecording]);

  useEffect(() => {
    return () => {
      cleanupStream();
      if (audioPreviewUrl) URL.revokeObjectURL(audioPreviewUrl);
    };
  }, [audioPreviewUrl, cleanupStream]);

  const startRecording = async () => {
    if (!task || submitting) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Audio recording is not supported in this browser.");
      return;
    }

    setError("");
    setAudioBlob(null);
    setAudioPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = preferredMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        setAudioBlob(blob);
        setAudioPreviewUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return URL.createObjectURL(blob);
        });
        setPhase("recorded");
        cleanupStream();
      };

      setSpeakLeft(task.speak_seconds);
      setPhase("recording");
      recorder.start();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not start recording. Check microphone permission."
      );
      cleanupStream();
    }
  };

  const submitRecording = async () => {
    if (!task || !audioBlob || submitting) return;
    setSubmitting(true);
    setUploadProgress(0);
    setError("");
    try {
      const submission = await api.submitSpeaking(task.id, audioBlob, setUploadProgress);
      router.push(`/speaking/result/${submission.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
      setSubmitting(false);
    }
  };

  const resetAttempt = () => {
    if (!task || submitting) return;
    stopRecording();
    setAudioBlob(null);
    setAudioPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    setPrepLeft(task.prep_seconds);
    setSpeakLeft(task.speak_seconds);
    setPhase(task.prep_seconds > 0 ? "prep" : "ready");
    setError("");
  };

  if (!ready || !token) return null;
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    );
  }
  if (!task && error) {
    return (
      <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
    );
  }
  if (!task) return null;

  const activeTime = phase === "prep" ? prepLeft : speakLeft;
  const activeLabel = phase === "prep" ? "Preparation" : "Answer";

  return (
    <div className="space-y-6">
      <div className="sticky top-[57px] z-20">
        <Card className="px-4 py-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Badge tone={partTone(task.part)}>Part {task.part}</Badge>
                <h1 className="truncate text-base font-bold text-slate-900">
                  Speaking Part {task.part}
                </h1>
              </div>
              <p className="mt-0.5 text-sm text-slate-500">
                {phase === "recorded"
                  ? "Recording ready to submit"
                  : phase === "ready"
                    ? "Ready to record"
                    : `${activeLabel} time`}
              </p>
            </div>
            <div
              className={`w-fit rounded-xl px-3 py-1.5 font-mono text-lg font-semibold ${
                phase === "recording"
                  ? "bg-red-100 text-red-700"
                  : "bg-slate-100 text-slate-700"
              }`}
            >
              {phase === "recorded" ? "Done" : formatTime(activeTime)}
            </div>
          </div>
        </Card>
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      <Card className={`p-6 ${task.part === 2 ? "border-slate-300" : ""}`}>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
          {task.part === 2 ? "Cue card" : "Examiner questions"}
        </h2>
        {task.part === 2 && (
          <p className="mb-4 text-sm font-medium text-slate-500">You should talk about this topic for one to two minutes.</p>
        )}
        <div className="space-y-3">
          {task.questions.map((question, index) => (
            <p key={question} className="flex gap-3 text-slate-700">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-700">
                {task.part === 2 && index > 0 ? "•" : index + 1}
              </span>
              <span>{question}</span>
            </p>
          ))}
        </div>
      </Card>

      <Card className="p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-slate-900">Recording</h2>
            <p className="mt-1 text-sm text-slate-500">
              {phase === "prep" &&
                "Use the preparation time to organise your answer."}
              {phase === "ready" && "Start recording when you are ready."}
              {phase === "recording" && "Speak clearly until the timer ends."}
              {phase === "recorded" && "Listen back or submit your recording."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {phase === "prep" && (
              <Button variant="secondary" onClick={() => {
                setPrepLeft(0);
                setPhase("ready");
              }}>
                Skip prep
              </Button>
            )}
            {phase !== "recording" && (
              <Button onClick={startRecording} disabled={submitting}>
                <Mic className="h-4 w-4" />
                {phase === "recorded" ? "Record again" : "Start recording"}
              </Button>
            )}
            {phase === "recording" && (
              <Button variant="secondary" onClick={stopRecording}>
                <Square className="h-4 w-4" />
                Stop
              </Button>
            )}
            {phase === "recorded" && (
              <Button variant="secondary" onClick={resetAttempt} disabled={submitting}>
                <RotateCcw className="h-4 w-4" />
                Restart with prep
              </Button>
            )}
          </div>
        </div>

        {audioPreviewUrl && (
          <audio controls src={audioPreviewUrl} className="mt-5 w-full">
            Your browser does not support audio.
          </audio>
        )}

        <Button
          onClick={submitRecording}
          disabled={!audioBlob || submitting}
          size="lg"
          className="mt-5 w-full"
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              {uploadProgress < 100 ? `Uploading ${uploadProgress}%` : "Reviewing response"}
            </>
          ) : "Submit recording"}
        </Button>
        {submitting && (
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-label={`Upload ${uploadProgress}%`}>
            <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${uploadProgress}%` }} />
          </div>
        )}
      </Card>
    </div>
  );
}
