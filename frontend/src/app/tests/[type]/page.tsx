"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, notFound } from "next/navigation";
import { api, Test } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LinkButton } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

const META: Record<
  string,
  { title: string; description: string; badge: "blue" | "violet" }
> = {
  reading: {
    title: "Reading",
    description: "Academic passages with a mix of IELTS question types.",
    badge: "blue",
  },
  listening: {
    title: "Listening",
    description: "Audio clips with comprehension questions and a live timer.",
    badge: "violet",
  },
};

export default function TestCategoryPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const type = String(params.type);
  const meta = META[type];

  const [tests, setTests] = useState<Test[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token || !meta) return;
    api
      .listTests()
      .then((all) => setTests(all.filter((t) => t.test_type === type)))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, type, meta]);

  if (!meta) return notFound();
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
        <div className="mt-3">
          <Badge tone={meta.badge} className="mb-3">
            IELTS {meta.title}
          </Badge>
          <h1 className="text-2xl font-bold text-slate-900">{meta.title} tests</h1>
          <p className="mt-1 text-slate-500">{meta.description}</p>
        </div>
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1].map((i) => (
            <Card key={i} className="p-5">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="mt-3 h-6 w-40" />
              <Skeleton className="mt-3 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-20" />
            </Card>
          ))}
        </div>
      ) : tests.length === 0 && !error ? (
        <Card className="p-10 text-center">
          <p className="text-slate-500">No {meta.title.toLowerCase()} tests available yet.</p>
          <div className="mt-4 flex justify-center">
            <LinkButton href="/" variant="secondary">
              Back to tests
            </LinkButton>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {tests.map((test, i) => (
            <Link
              key={test.id}
              href={`/test/${test.id}`}
              className="group animate-fade-up"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <Card className="h-full p-5 transition duration-300 group-hover:-translate-y-1 group-hover:border-blue-300 group-hover:shadow-lg">
                <Badge tone={meta.badge}>{test.test_type}</Badge>
                <h3 className="mt-3 text-lg font-semibold text-slate-900">
                  {test.title}
                </h3>
                {test.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500">
                    {test.description}
                  </p>
                )}
                <div className="mt-4 flex items-center gap-1.5 text-sm text-slate-400">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <circle cx="12" cy="12" r="9" />
                    <path strokeLinecap="round" d="M12 7v5l3 2" />
                  </svg>
                  {test.duration_minutes} min
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
