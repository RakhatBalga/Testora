import Link from "next/link";
import { Trophy, UserRound } from "lucide-react";
import { LinkButton, Skeleton } from "@/shared/ui";
import type { RecentItem } from "@/entities/profile";
import { routes } from "@/shared/config";

export function RecentActivityList({ loading, items }: { loading: boolean; items: RecentItem[] }) {
  return (
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:140ms]">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-amber-500" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Recent activity</h2>
          </div>
          <Link href={routes.practice()} className="text-sm font-semibold text-[var(--brand)]">
            Practice
          </Link>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-14 w-full rounded-xl" />
            ))}
          </div>
        ) : items.length > 0 ? (
          <div className="space-y-2.5">
            {items.map((item) => (
              <RecentRow key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-[var(--border)] bg-slate-50/60 p-6 text-center">
            <UserRound className="mx-auto h-7 w-7 text-slate-300" />
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Your completed tests and AI reviews will appear here.
            </p>
            <LinkButton href={routes.practice()} size="sm" className="mt-4">
              Start practice
            </LinkButton>
          </div>
        )}
      </section>
  );
}

function RecentRow({ item }: { item: RecentItem }) {
  return (
    <Link
      href={item.href}
      className="group flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] px-4 py-3 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-[var(--text-primary)]">
          {item.title}
        </span>
        <span className="mt-0.5 block text-xs capitalize text-[var(--text-secondary)]">
          {item.meta}
        </span>
      </span>
      <span className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-semibold capitalize ${item.badgeClass}`}>
        {item.badge}
      </span>
    </Link>
  );
}
