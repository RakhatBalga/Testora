"use client";

import { useEffect, useState, ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  AttemptSummary,
  WritingSubmissionSummary,
  SpeakingSubmissionSummary,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Card } from "@/components/ui/Card";
import { Button, LinkButton } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Reveal } from "@/components/Reveal";

function roundHalf(n: number): number {
  return Math.round(n * 2) / 2;
}

function bandTone(band: number | null): string {
  if (band === null) return "bg-slate-100 text-slate-500";
  if (band >= 7) return "bg-green-50 text-green-700";
  if (band >= 5.5) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

function scoreTone(percent: number): string {
  if (percent >= 70) return "bg-green-50 text-green-700";
  if (percent >= 40) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

export default function ProfilePage() {
  const { token, ready } = useRequireAuth();
  const { username, logout } = useAuth();
  const router = useRouter();

  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [writing, setWriting] = useState<WritingSubmissionSummary[]>([]);
  const [speaking, setSpeaking] = useState<SpeakingSubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    Promise.all([
      api.listAttempts(),
      api.listWritingSubmissions(),
      api.listSpeakingSubmissions(),
    ])
      .then(([a, w, s]) => {
        setAttempts(a);
        setWriting(w);
        setSpeaking(s);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (!ready || !token) return null;

  const taken = attempts.length;
  const tasksDone = writing.length + speaking.length;
  const totalSessions = taken + tasksDone;

  // Average/best across every graded item (Reading, Listening, Writing, Speaking)
  // on the IELTS 0–9 band scale, rounded to the nearest half-band.
  const bands = [
    ...attempts.map((a) => a.band),
    ...writing.map((w) => w.band),
    ...speaking.map((s) => s.band),
  ].filter((b): b is number => b !== null);
  const avgBand =
    bands.length === 0
      ? null
      : roundHalf(bands.reduce((sum, b) => sum + b, 0) / bands.length);
  const bestBand = bands.length === 0 ? null : Math.max(...bands);

  return (
    <div className="space-y-10">
      {/* Header */}
      <Card className="animate-fade-up overflow-hidden">
        <div className="bg-hero relative flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand)] text-2xl font-bold text-white shadow-sm">
              {username?.[0]?.toUpperCase() ?? "?"}
            </span>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{username}</h1>
              <p className="text-sm text-slate-500">Your IELTS practice profile</p>
            </div>
          </div>
          <Button variant="secondary" onClick={handleLogout} className="w-fit">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12H4m0 0l3.5-3.5M4 12l3.5 3.5M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" />
            </svg>
            Log out
          </Button>
        </div>
      </Card>

      {/* Stats */}
      <div className="grid animate-fade-up gap-4 [animation-delay:80ms] sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total sessions" value={loading ? null : String(totalSessions)} />
        <StatCard
          label="Average band"
          value={loading ? null : avgBand === null ? "—" : avgBand.toFixed(1)}
        />
        <StatCard
          label="Best band"
          value={loading ? null : bestBand === null ? "—" : bestBand.toFixed(1)}
        />
        <StatCard
          label="AI sessions"
          value={loading ? null : String(tasksDone)}
        />
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : (
        <div className="space-y-10">
          {/* Reading & Listening */}
          <ResultSection
            title="Reading & Listening"
            empty="No tests taken yet."
            href="/practice"
            cta="Take a test"
            items={attempts.map((a) => {
              const percent = Math.round((a.score / a.total) * 100);
              return (
                <ResultRow
                  key={`a-${a.id}`}
                  href={`/result/${a.id}`}
                  title={a.test_title}
                  meta={`${a.test_type} · ${new Date(a.created_at).toLocaleDateString()}`}
                  badge={`${a.score} / ${a.total}`}
                  badgeClass={scoreTone(percent)}
                />
              );
            })}
          />

          {/* Writing */}
          <ResultSection
            title="Writing"
            empty="No writing submissions yet."
            href="/writing"
            cta="Practise writing"
            items={writing.map((w) => (
              <ResultRow
                key={`w-${w.id}`}
                href={`/writing/result/${w.id}`}
                title={w.task_title}
                meta={`${w.word_count} words · ${new Date(w.created_at).toLocaleDateString()}`}
                badge={w.band === null ? w.status : `Band ${w.band.toFixed(1)}`}
                badgeClass={bandTone(w.band)}
              />
            ))}
          />

          {/* Speaking */}
          <ResultSection
            title="Speaking"
            empty="No speaking submissions yet."
            href="/speaking"
            cta="Practise speaking"
            items={speaking.map((s) => (
              <ResultRow
                key={`s-${s.id}`}
                href={`/speaking/result/${s.id}`}
                title={`Speaking Part ${s.task_part}`}
                meta={new Date(s.created_at).toLocaleDateString()}
                badge={s.band === null ? "submitted" : `Band ${s.band.toFixed(1)}`}
                badgeClass={bandTone(s.band)}
              />
            ))}
          />
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | null }) {
  return (
    <Card className="p-5">
      <p className="text-sm text-slate-500">{label}</p>
      {value === null ? (
        <Skeleton className="mt-2 h-9 w-16" />
      ) : (
        <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
      )}
    </Card>
  );
}

function ResultSection({
  title,
  items,
  empty,
  href,
  cta,
}: {
  title: string;
  items: ReactNode[];
  empty: string;
  href: string;
  cta: string;
}) {
  return (
    <Reveal>
      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">{title}</h2>
        {items.length === 0 ? (
          <Card className="flex flex-col items-center gap-3 p-8 text-center">
            <p className="text-slate-500">{empty}</p>
            <LinkButton href={href} variant="secondary" size="sm">
              {cta}
            </LinkButton>
          </Card>
        ) : (
          <div className="space-y-3">{items}</div>
        )}
      </section>
    </Reveal>
  );
}

function ResultRow({
  href,
  title,
  meta,
  badge,
  badgeClass,
}: {
  href: string;
  title: string;
  meta: string;
  badge: string;
  badgeClass: string;
}) {
  return (
    <Link href={href} className="group block">
      <Card className="flex items-center justify-between p-4 transition duration-300 group-hover:-translate-y-0.5 group-hover:border-blue-300 group-hover:shadow-md">
        <div className="min-w-0">
          <p className="truncate font-medium text-slate-900">{title}</p>
          <p className="text-sm capitalize text-slate-400">{meta}</p>
        </div>
        <span
          className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold capitalize ${badgeClass}`}
        >
          {badge}
        </span>
      </Card>
    </Link>
  );
}
