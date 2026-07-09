"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { api } from "@/shared/api";
import { useAuth } from "@/shared/auth";
import { IELTS_TARGET_BAND } from "@/shared/config";
import { AccountExistsModal, AuthField, AuthShell, GoogleSignInButton } from "@/features/auth";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [accountExists, setAccountExists] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      // Target band defaults to 7.5 here and is editable later in the profile.
      await api.register(username, password, IELTS_TARGET_BAND);
      const res = await api.login(username, password);
      login(res.access_token, username);
      router.push("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      // Surface a friendly modal instead of a raw "already taken" error.
      if (/already (taken|exists|registered)/i.test(message)) {
        setAccountExists(true);
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  const primaryBtn =
    "inline-flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-[var(--brand)] px-6 text-base font-semibold text-white shadow-sm shadow-[var(--brand)]/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-[var(--brand-dark)] hover:shadow-lg hover:shadow-[var(--brand)]/30 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-sm";

  return (
    <AuthShell
      panel={{
        eyebrow: "Welcome to Testora",
        title: "You're one step away from your IELTS goals.",
        subtitle: "Create your account and start practising with real feedback today.",
      }}
    >
      <div className="animate-fade-up">
        <h1 className="text-[2rem] font-extrabold tracking-tight text-[var(--text-primary)]">
          Create your account
        </h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Start preparing for your target IELTS score today — you can set your goal band anytime in your profile.
        </p>

        {error && (
          <p className="mt-6 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mt-8 space-y-4">
            <AuthField
              label="Username"
              name="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              autoFocus
            />
            <AuthField
              label="Password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !username || !password}
            className={`mt-8 ${primaryBtn}`}
          >
            {loading ? (
              "Creating account..."
            ) : (
              <>
                Create account
                <Sparkles className="h-5 w-5" />
              </>
            )}
          </button>
        </form>

        <div className="my-6 flex items-center gap-4">
          <div className="h-px flex-1 bg-[var(--border)]" />
          <span className="text-sm font-medium text-[var(--text-secondary)]">or</span>
          <div className="h-px flex-1 bg-[var(--border)]" />
        </div>

        <GoogleSignInButton
          signupData={{ username: username.trim() || undefined }}
        />
      </div>

      <p className="mt-8 text-center text-sm text-[var(--text-secondary)]">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-[var(--brand)] hover:underline">
          Sign in
        </Link>
      </p>

      <AccountExistsModal open={accountExists} onClose={() => setAccountExists(false)} />
    </AuthShell>
  );
}
