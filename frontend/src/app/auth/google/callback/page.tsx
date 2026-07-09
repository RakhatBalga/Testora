"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/shared/api";
import { useAuth } from "@/shared/auth";
import { GOOGLE_SIGNUP_KEY } from "@/features/auth/ui/GoogleSignInButton";

type Phase = "working" | "pick-username" | "error";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [phase, setPhase] = useState<Phase>("working");
  const [error, setError] = useState("");
  const [nick, setNick] = useState("");
  const [nickError, setNickError] = useState("");
  const [saving, setSaving] = useState(false);
  const tokenRef = useRef("");
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    // All setState happens in async continuations (the lint rule forbids
    // synchronous setState inside the effect body).
    const run = async () => {
      const code = searchParams?.get("code") ?? null;
      if (!code) {
        throw new Error("No authorization code received from Google.");
      }

      // Register-flow choices stashed before the OAuth redirect.
      let signup: { username?: string; target_band?: number } | undefined;
      try {
        const raw = sessionStorage.getItem(GOOGLE_SIGNUP_KEY);
        if (raw) signup = JSON.parse(raw);
      } catch {
        // corrupted stash — ignore
      }
      sessionStorage.removeItem(GOOGLE_SIGNUP_KEY);

      const redirectUri = `${window.location.origin}/auth/google/callback`;
      const res = await api.googleAuth(code, redirectUri, signup);
      login(res.access_token, res.username);
      if (res.is_new_user && !signup?.username) {
        // Signed up via the login page — let them pick a nickname now,
        // before they ever see the auto-generated one.
        tokenRef.current = res.access_token;
        setNick(res.username);
        setPhase("pick-username");
        return;
      }
      router.push("/");
    };

    run().catch((err) => {
      setError(err instanceof Error ? err.message : "Google sign-in failed");
      setPhase("error");
    });
  }, [searchParams, login, router]);

  const saveNick = async (e: React.FormEvent) => {
    e.preventDefault();
    setNickError("");
    const trimmed = nick.trim();
    if (trimmed.length < 3) {
      setNickError("Username must be at least 3 characters.");
      return;
    }
    setSaving(true);
    try {
      const res = await api.setUsername(trimmed);
      login(res.access_token, trimmed);
      router.push("/");
    } catch (err) {
      setNickError(err instanceof Error ? err.message : "Could not set username");
      setSaving(false);
    }
  };

  if (phase === "pick-username") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--background)] px-4">
        <div className="w-full max-w-md rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-sm">
          <h1 className="text-2xl font-extrabold tracking-tight text-[var(--text-primary)]">
            Choose your username
          </h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            This is how you&apos;ll appear in Testora. You can keep the suggestion.
          </p>
          <form onSubmit={saveNick} className="mt-6 space-y-4">
            {nickError && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{nickError}</p>
            )}
            <input
              value={nick}
              onChange={(e) => setNick(e.target.value)}
              autoFocus
              minLength={3}
              maxLength={50}
              className="h-[54px] w-full rounded-2xl border border-[var(--border)] bg-white px-4 text-base text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--brand)]"
              placeholder="Username"
            />
            <button
              type="submit"
              disabled={saving || nick.trim().length < 3}
              className="h-[54px] w-full rounded-2xl bg-[var(--brand)] text-base font-semibold text-white transition-colors hover:bg-[var(--brand-dark)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving..." : "Continue"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--background)]">
        <div className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
            <svg className="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Sign-in failed</h2>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="mt-6 rounded-xl bg-[var(--brand)] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[var(--brand-dark)]"
          >
            Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--background)]">
      <div className="text-center">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--brand)]" />
        <p className="text-sm text-[var(--text-secondary)]">Signing you in...</p>
      </div>
    </div>
  );
}
