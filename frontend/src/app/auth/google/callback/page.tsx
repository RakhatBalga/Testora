"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/shared/api";
import { useAuth } from "@/shared/auth";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [error, setError] = useState("");
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const code = searchParams?.get("code") ?? null;
    if (!code) {
      setError("No authorization code received from Google.");
      return;
    }

    const redirectUri = `${window.location.origin}/auth/google/callback`;

    api
      .googleAuth(code, redirectUri)
      .then((res) => {
        login(res.access_token, "");
        api.getProfile().then((profile) => {
          login(res.access_token, profile.username);
          router.push("/");
        });
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Google sign-in failed");
      });
  }, [searchParams, login, router]);

  if (error) {
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
