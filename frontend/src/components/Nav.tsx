"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { LinkButton } from "@/components/ui/Button";

export default function Nav() {
  const { token, username, ready } = useAuth();
  const pathname = usePathname();
  const onProfile = pathname?.startsWith("/profile");

  return (
    <nav className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="group flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white transition-transform duration-300 group-hover:scale-105">
            T
          </span>
          <span className="text-lg font-bold text-slate-900">Testora</span>
        </Link>

        <div className="flex items-center gap-2 text-sm">
          {!ready ? null : token ? (
            <Link
              href="/profile"
              aria-current={onProfile ? "page" : undefined}
              className={`group flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 transition ${
                onProfile
                  ? "border-blue-200 bg-blue-50"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-violet-500 text-xs font-semibold text-white">
                {username?.[0]?.toUpperCase() ?? "?"}
              </span>
              <span
                className={`font-medium ${
                  onProfile ? "text-blue-700" : "text-slate-700 group-hover:text-slate-900"
                }`}
              >
                {username ?? "Profile"}
              </span>
            </Link>
          ) : (
            <>
              <LinkButton href="/login" variant="ghost" size="sm">
                Log in
              </LinkButton>
              <LinkButton href="/register" size="sm">
                Get started
              </LinkButton>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
