"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

/**
 * Decides which "chrome" wraps the page.
 *
 * The public landing page (`/` while logged out) renders its own full-bleed
 * navbar and footer, so we hide the app Nav/Footer and the constrained <main>
 * there. Every other route gets the standard app shell.
 */
export default function Shell({ children }: { children: React.ReactNode }) {
  const { token, ready } = useAuth();
  const pathname = usePathname();

  // Auth pages bring their own guest navbar and full-bleed layout — no app
  // chrome, and no need to wait for auth state.
  const isAuth = pathname === "/login" || pathname === "/register";
  if (isAuth) return <>{children}</>;

  // Avoid a flash of the wrong chrome before auth state is known.
  if (!ready) return <div className="flex-1" />;

  const isLanding = pathname === "/" && !token;
  if (isLanding) return <>{children}</>;

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
      <Footer />
    </>
  );
}
