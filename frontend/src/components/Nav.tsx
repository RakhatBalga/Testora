"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Dumbbell,
  ClipboardCheck,
  BookMarked,
  BarChart3,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { LinkButton } from "@/components/ui/Button";

const LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/practice", label: "Practice", icon: Dumbbell },
  { href: "/mock-tests", label: "Mock Tests", icon: ClipboardCheck },
  { href: "/vocabulary", label: "Vocabulary", icon: BookMarked },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Nav() {
  const { token, username, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname?.startsWith(`${href}/`);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <nav className="sticky top-0 z-40 border-b border-[var(--border)] bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
        <div className="flex items-center gap-8">
          <Link href="/" className="group flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--brand)] text-sm font-bold text-white transition-transform duration-300 group-hover:scale-105">
              T
            </span>
            <span className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
              Testora
            </span>
          </Link>

          {token && (
            <div className="hidden items-center gap-1 lg:flex">
              {LINKS.map((l) => {
                const active = isActive(l.href, l.exact);
                return (
                  <Link
                    key={l.href}
                    href={l.href}
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
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setMenuOpen((v) => !v)}
                  className="flex items-center gap-2 rounded-full border border-[var(--border)] py-1 pl-1 pr-3 transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--brand)] text-xs font-semibold text-white">
                    {username?.[0]?.toUpperCase() ?? "?"}
                  </span>
                  <span className="hidden text-sm font-medium text-[var(--text-primary)] sm:block">
                    {username ?? "Profile"}
                  </span>
                </button>
                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-44 overflow-hidden rounded-xl border border-[var(--border)] bg-white py-1 shadow-lg shadow-slate-200/60">
                    <Link
                      href="/profile"
                      className="block px-4 py-2.5 text-sm text-[var(--text-primary)] hover:bg-slate-50"
                    >
                      Profile
                    </Link>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => setMobileOpen((v) => !v)}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-secondary)] hover:bg-slate-50 lg:hidden"
                aria-label="Toggle menu"
              >
                {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </>
          ) : (
            <>
              <LinkButton href="/login" variant="ghost" size="sm">
                Sign in
              </LinkButton>
              <LinkButton href="/register" size="sm">
                Get started
              </LinkButton>
            </>
          )}
        </div>
      </div>

      {/* mobile section menu */}
      {token && mobileOpen && (
        <div className="border-t border-[var(--border)] bg-white px-5 py-3 lg:hidden">
          <div className="grid gap-1">
            {LINKS.map((l) => {
              const active = isActive(l.href, l.exact);
              return (
                <Link
                  key={l.href}
                  href={l.href}
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
          </div>
        </div>
      )}
    </nav>
  );
}
