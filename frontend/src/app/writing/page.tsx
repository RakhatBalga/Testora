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

// Human-readable labels for the essay-type slugs stored on each task. Unknown
// slugs fall back to a prettified version so new types render without a code
// change here.
const ESSAY_TYPE_LABELS: Record<string, string> = {
  bar_chart: "Bar chart",
  line_graph: "Line graph",
  pie_chart: "Pie chart",
  table: "Table",
  process: "Process",
  map: "Map",
  mixed: "Mixed",
  opinion: "Opinion",
  discussion: "Discussion",
  advantages_disadvantages: "Advantages / Disadvantages",
  problem_solution: "Problem / Solution",
  two_part: "Two-part question",
};

function essayTypeLabel(slug: string): string {
  return (
    ESSAY_TYPE_LABELS[slug] ??
    slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

function buildWritingHref(taskType: number | null, essayType: string | null): string {
  const params = new URLSearchParams();
  if (taskType) params.set("task", String(taskType));
  if (essayType) params.set("type", essayType);
  const query = params.toString();
  return query ? `/writing?${query}` : "/writing";
}

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
  const activeEssayType = searchParams?.get("type") ?? null;
  const taskCounts = useMemo(
    () => ({
      all: tasks.length,
      task1: tasks.filter((task) => task.task_type === 1).length,
      task2: tasks.filter((task) => task.task_type === 2).length,
    }),
    [tasks],
  );

  // Tasks in scope of the active Task 1/2 tab — the essay-type chips and the
  // visible list are both derived from this so the two filters compose.
  const tasksInTaskScope = useMemo(
    () =>
      activeTaskType
        ? tasks.filter((task) => task.task_type === activeTaskType)
        : tasks,
    [tasks, activeTaskType],
  );

  // Distinct essay types present in scope, with counts — only render chips for
  // types that actually have tasks, so the filter never leads to an empty list.
  const essayTypeOptions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const task of tasksInTaskScope) {
      if (!task.essay_type) continue;
      counts.set(task.essay_type, (counts.get(task.essay_type) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([slug, count]) => ({ slug, count, label: essayTypeLabel(slug) }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [tasksInTaskScope]);

  const visibleTasks = activeEssayType
    ? tasksInTaskScope.filter((task) => task.essay_type === activeEssayType)
    : tasksInTaskScope;

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
        <p className="mb-2 mt-3 text-sm font-semibold uppercase tracking-wider text-[var(--brand)]">
          IELTS Writing
        </p>
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

      {essayTypeOptions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Essay type
          </span>
          <Link
            href={buildWritingHref(activeTaskType, null)}
            className={`inline-flex h-8 items-center rounded-full border px-3 text-sm font-medium transition ${
              activeEssayType === null
                ? "border-[var(--brand)] bg-[var(--brand)]/10 text-[var(--brand)]"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950"
            }`}
          >
            All types
          </Link>
          {essayTypeOptions.map((option) => {
            const active = option.slug === activeEssayType;
            return (
              <Link
                key={option.slug}
                href={buildWritingHref(activeTaskType, option.slug)}
                className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-sm font-medium transition ${
                  active
                    ? "border-[var(--brand)] bg-[var(--brand)]/10 text-[var(--brand)]"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950"
                }`}
              >
                {option.label}
                <span
                  className={`rounded-full px-1.5 text-xs ${
                    active ? "bg-[var(--brand)]/15 text-[var(--brand)]" : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {option.count}
                </span>
              </Link>
            );
          })}
        </div>
      )}

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
              <Card className="h-full p-5 transition duration-300 group-hover:-translate-y-1 group-hover:shadow-lg">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={taskTone(task.task_type)}>
                    Task {task.task_type}
                  </Badge>
                  {task.essay_type && (
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                      {essayTypeLabel(task.essay_type)}
                    </span>
                  )}
                </div>
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
