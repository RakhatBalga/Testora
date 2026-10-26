import Link from "next/link";
import { Activity, ArrowRight, BookOpen, Headphones, Mic, PenLine } from "lucide-react";
import { Skeleton } from "@/shared/ui";
import { routes } from "@/shared/config";

export function PracticeRecord({
  loading,
  readingCount,
  listeningCount,
  writingCount,
  speakingCount,
}: {
  loading: boolean;
  readingCount: number;
  listeningCount: number;
  writingCount: number;
  speakingCount: number;
}) {
  return (
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:120ms]">
        <div className="mb-5 flex items-center gap-2">
          <Activity className="h-5 w-5 text-[var(--brand)]" />
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Practice record</h2>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 w-full rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            <SkillRow icon={<BookOpen className="h-5 w-5" />} label="Reading" value={readingCount} href={routes.reading.library()} />
            <SkillRow icon={<Headphones className="h-5 w-5" />} label="Listening" value={listeningCount} href={routes.listening.library()} />
            <SkillRow icon={<PenLine className="h-5 w-5" />} label="Writing" value={writingCount} href={routes.writing.library()} />
            <SkillRow icon={<Mic className="h-5 w-5" />} label="Speaking" value={speakingCount} href={routes.speaking.library()} />
          </div>
        )}
      </section>
  );
}

function SkillRow({
  icon,
  label,
  value,
  href,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center justify-between rounded-xl border border-[var(--border)] px-4 py-3 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <span className="flex items-center gap-3">
        <span className="flex h-8 w-8 items-center justify-center text-[var(--brand)]">
          {icon}
        </span>
        <span className="text-sm font-semibold text-[var(--text-primary)]">{label}</span>
      </span>
      <span className="flex items-center gap-2 text-sm font-semibold text-[var(--text-secondary)]">
        {value}
        <ArrowRight className="h-4 w-4 text-slate-300 transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
      </span>
    </Link>
  );
}
