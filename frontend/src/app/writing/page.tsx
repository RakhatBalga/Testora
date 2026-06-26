"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, WritingTask } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Badge } from "@/shared/ui";
import { Card } from "@/shared/ui";
import { Skeleton } from "@/shared/ui";

function taskTone(taskType: number) {
  return taskType === 1 ? "blue" : "violet";
}

const TASK_FILTERS = [
  { label: "All", href: "/writing", taskType: null },
  { label: "Task 1", href: "/writing?task=1", taskType: 1 },
  { label: "Task 2", href: "/writing?task=2", taskType: 2 },
];

export default function WritingPage() {
  const { token, ready } = useRequireAuth();
  const searchParams = useSearchParams();
  const [tasks, setTasks] = useState<WritingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api
      .listWritingTasks()
      .then(setTasks)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const taskParam = searchParams?.get("task") ?? null;
  const activeTaskType = taskParam === "1"
    ? 1
    : taskParam === "2"
      ? 2
      : null;
  const taskCounts = useMemo(
    () => ({
      all: tasks.length,
      task1: tasks.filter((task) => task.task_type === 1).length,
      task2: tasks.filter((task) => task.task_type === 2).length,
    }),
    [tasks],
  );
  const visibleTasks = activeTaskType
    ? tasks.filter((task) => task.task_type === activeTaskType)
    : tasks;

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
        <Badge tone="green" className="mb-3 mt-3 block w-fit">
          IELTS Writing
        </Badge>
        <h1 className="text-2xl font-bold text-slate-900">Writing tasks</h1>
        <p className="mt-1 text-slate-500">
          Practise Task 1 and Task 2, then get band feedback by criterion.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {TASK_FILTERS.map((filter) => {
          const active = filter.taskType === activeTaskType;
          const count = filter.taskType === null
            ? taskCounts.all
            : filter.taskType === 1
              ? taskCounts.task1
              : taskCounts.task2;
          return (
            <Link
              key={filter.label}
              href={filter.href}
              className={`inline-flex h-10 items-center gap-2 rounded-lg border px-3 text-sm font-semibold transition ${
                active
                  ? "border-slate-900 bg-slate-900 text-white shadow-sm"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950"
              }`}
            >
              {filter.label}
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  active ? "bg-white/15 text-white" : "bg-slate-100 text-slate-500"
                }`}
              >
                {count}
              </span>
            </Link>
          );
        })}
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1].map((i) => (
            <Card key={i} className="p-5">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="mt-3 h-6 w-48" />
              <Skeleton className="mt-3 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-3/4" />
              <Skeleton className="mt-5 h-4 w-32" />
            </Card>
          ))}
        </div>
      ) : visibleTasks.length === 0 && !error ? (
        <Card className="p-8 text-center text-slate-500">
          No writing tasks available yet.
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {visibleTasks.map((task, i) => (
            <Link
              key={task.id}
              href={`/writing/${task.id}`}
              className="group animate-fade-up"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <Card className="h-full p-5 transition duration-300 group-hover:-translate-y-1 group-hover:border-emerald-300 group-hover:shadow-lg">
                <Badge tone={taskTone(task.task_type)}>
                  Task {task.task_type}
                </Badge>
                <h2 className="mt-3 text-lg font-semibold text-slate-900">
                  {task.title}
                </h2>
                <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-slate-500">
                  {task.prompt}
                </p>
                <div className="mt-5 flex flex-wrap gap-2 text-sm text-slate-500">
                  <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                    {task.duration_minutes} min
                  </span>
                  <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                    {task.min_words}+ words
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
