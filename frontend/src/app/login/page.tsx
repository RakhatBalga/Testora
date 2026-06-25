"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import AuthShell from "@/components/auth/AuthShell";
import { AuthField } from "@/components/auth/AuthField";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login(username, password);
      login(res.access_token, username);
      const next = new URLSearchParams(window.location.search).get("next");
      // Only honour same-site relative paths to avoid open-redirect abuse.
      router.push(next && next.startsWith("/") ? next : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      panel={{
        title: (
          <>
            Practice with purpose, <span className="text-white/60">score higher.</span>
          </>
        ),
        subtitle: "Real IELTS practice with instant feedback and measurable progress.",
      }}
    >
      <h1 className="text-[2rem] font-extrabold tracking-tight text-[var(--text-primary)]">
        Sign in
      </h1>
      <p className="mt-2 text-[var(--text-secondary)]">
        Welcome back — continue your IELTS preparation.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        {error && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
        )}

        <AuthField
          label="Email or username"
          name="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoComplete="username"
        />

        <AuthField
          label="Password"
          name="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        <div className="flex justify-end">
          <Link
            href="/login"
            className="text-sm font-semibold text-[var(--brand)] hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="h-[54px] w-full rounded-2xl bg-[var(--brand)] text-base font-semibold text-white shadow-sm shadow-[var(--brand)]/25 transition-all duration-200 hover:bg-[var(--brand-dark)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-[var(--text-secondary)]">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="font-semibold text-[var(--brand)] hover:underline">
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}
