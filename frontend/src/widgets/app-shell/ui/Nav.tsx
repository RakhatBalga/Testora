"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import {
  CalendarCheck,
  LayoutDashboard,
  Dumbbell,
  BarChart3,
  BookMarked,
  History,
  Languages,
  LogOut,
  Menu,
  UserRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/shared/auth";
import { routes } from "@/shared/config";
import { mediaUrl } from "@/shared/api";
import { LinkButton } from "@/shared/ui";

const LINKS: { href: string; label: string; icon: LucideIcon; exact?: boolean; also?: string[] }[] = [
  { href: routes.dashboard(), label: "Dashboard", icon: LayoutDashboard, exact: true },
  {
    href: routes.practice(),
    label: "Practice",
    icon: Dumbbell,
    // The skill pages are part of Practice.
    also: [routes.reading.library(), routes.listening.library(), routes.writing.library(), routes.speaking.library()],
  },
  { href: routes.studyPlan(), label: "Study plan", icon: CalendarCheck },
  { href: routes.analytics(), label: "Analytics", icon: BarChart3 },
  { href: routes.mistakes(), label: "Mistakes", icon: BookMarked },
  { href: routes.vocabulary(), label: "Vocabulary", icon: Languages },
  { href: routes.history(), label: "History", icon: History },
];

export default function Nav() {
  const { token, username, avatar, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setMobileOpen(false), 0);
    return () => window.clearTimeout(timer);
  }, [pathname]);

  const isActive = (href: string, exact?: boolean, also: string[] = []) =>
    exact
      ? pathname === href
      : [href, ...also].some((base) => pathname === base || pathname?.startsWith(`${base}/`));

  const handleLogout = () => {
    logout();
    router.push(routes.login());
  };

  return (
    <nav className="sticky top-0 z-40 border-b border-[var(--border)] bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
        <div className="flex items-center gap-8">
          <Link href={routes.dashboard()} className="group flex items-center gap-2.5">
            <Image
              src="/logo.svg"
              alt="Testora"
              width={32}
              height={32}
              className="h-8 w-8 object-contain transition-transform duration-300 group-hover:scale-105"
            />
            <span className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
              Testora
            </span>
          </Link>

          {token && (
            <div className="hidden items-center gap-1 lg:flex">
              {LINKS.map((l) => {
                const active = isActive(l.href, l.exact, l.also);
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      active
                        ? "bg-[var(--brand)]/[0.08] text-[var(--brand)]"
                        : "text-[var(--text-secondary)] hover:bg-slate-50 hover:text-[var(--text-primary)]"
                    }`}
                  >
                    <l.icon className="h-4 w-4" />
                    {l.label}
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {!ready ? null : token ? (
            <>
              <Link
                href={routes.profile()}
                className={`flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 transition ${
                  isActive(routes.profile())
                    ? "border-[var(--brand)]/30 bg-[var(--brand)]/[0.06]"
                    : "border-[var(--border)] hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                {avatar ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={mediaUrl(avatar) ?? undefined}
                    alt=""
                    className="h-7 w-7 rounded-full object-cover"
                  />
                ) : (
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--brand)] text-xs font-semibold text-white">
                    {username?.[0]?.toUpperCase() ?? "?"}
                  </span>
                )}
                <span className="hidden text-sm font-medium text-[var(--text-primary)] sm:block">
                  {username ?? "Profile"}
                </span>
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="hidden h-9 w-9 items-center justify-center rounded-lg text-[var(--text-secondary)] transition hover:bg-red-50 hover:text-red-600 sm:flex"
                aria-label="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setMobileOpen((v) => !v)}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-secondary)] hover:bg-slate-50 lg:hidden"
                aria-label="Toggle menu"
                aria-expanded={mobileOpen}
                aria-controls="mobile-menu"
              >
                {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </>
          ) : (
            <>
              <LinkButton href={routes.login()} variant="ghost" size="sm">
                Sign in
              </LinkButton>
              <LinkButton href={routes.register()} size="sm">
                Get started
              </LinkButton>
            </>
          )}
        </div>
      </div>

      {/* mobile section menu */}
      {token && mobileOpen && (
        <div id="mobile-menu" className="border-t border-[var(--border)] bg-white px-5 py-3 lg:hidden">
          <div className="grid gap-1">
            <Link
              href={routes.profile()}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive(routes.profile())
                  ? "bg-[var(--brand)]/[0.08] text-[var(--brand)]"
                  : "text-[var(--text-secondary)] hover:bg-slate-50"
              }`}
            >
              <UserRound className="h-4 w-4" />
              Profile
            </Link>
            {LINKS.map((l) => {
              const active = isActive(l.href, l.exact, l.also);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    active
                      ? "bg-[var(--brand)]/[0.08] text-[var(--brand)]"
                      : "text-[var(--text-secondary)] hover:bg-slate-50"
                  }`}
                >
                  <l.icon className="h-4 w-4" />
                  {l.label}
                </Link>
              );
            })}
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
