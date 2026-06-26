"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, SpeakingTask } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Badge } from "@/shared/ui";
import { Card } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

function partTone(part: number) {
  if (part === 1) return "blue";
  if (part === 2) return "violet";
  return "green";
}

export default function SpeakingPage() {
  const { token, ready } = useRequireAuth();
  const [tasks, setTasks] = useState<SpeakingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api
      .listSpeakingTasks()
      .then(setTasks)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (!ready || !token) return null;

  return (
    <div className="space-y-8">
      <div className="animate-fade-up">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-slate-500 transition hover:text-slate-900"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 6l-6 6 6 6" />
          </svg>
          All tests
        </Link>
        <Badge tone="slate" className="mb-3 mt-3 block w-fit">
          IELTS Speaking
        </Badge>
        <h1 className="text-2xl font-bold text-slate-900">Speaking practice</h1>
        <p className="mt-1 text-slate-500">
          Record your answer and save it for AI feedback when grading is enabled.
        </p>
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i} className="p-5">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="mt-3 h-6 w-40" />
              <Skeleton className="mt-3 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-3/4" />
              <Skeleton className="mt-5 h-4 w-28" />
            </Card>
          ))}
        </div>
      ) : tasks.length === 0 && !error ? (
        <Card className="p-8 text-center text-slate-500">
          No speaking tasks available yet.
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          {tasks.map((task, i) => (
            <Link
              key={task.id}
              href={`/speaking/${task.id}`}
              className="group animate-fade-up"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <Card className="h-full p-5 transition duration-300 group-hover:-translate-y-1 group-hover:border-amber-300 group-hover:shadow-lg">
                <Badge tone={partTone(task.part)}>Part {task.part}</Badge>
                <h2 className="mt-3 text-lg font-semibold text-slate-900">
                  Speaking Part {task.part}
                </h2>
                <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-slate-500">
                  {task.questions[0] ?? "Speaking prompt"}
                </p>
                <div className="mt-5 flex flex-wrap gap-2 text-sm text-slate-500">
                  <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                    {task.prep_seconds}s prep
                  </span>
                  <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                    {task.speak_seconds}s speak
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
