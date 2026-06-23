"use client";

import { useRouter } from "next/navigation";
import { UserCheck, X, KeyRound, ArrowRight } from "lucide-react";

export default function AccountExistsModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="account-exists-title"
    >
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm animate-fade" onClick={onClose} />

      <div className="relative w-full max-w-md animate-scale-in rounded-3xl border border-[var(--border)] bg-white p-7 shadow-2xl shadow-slate-900/20">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
        >
          <X className="h-5 w-5" />
        </button>

        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand)]/[0.1] text-[var(--brand)]">
          <UserCheck className="h-7 w-7" />
        </span>

        <h2
          id="account-exists-title"
          className="mt-5 text-xl font-extrabold tracking-tight text-[var(--text-primary)]"
        >
          Account already exists
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
          We found an account associated with this username. Sign in to continue your IELTS
          preparation, or reset your password if you&apos;ve forgotten it.
        </p>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-2xl bg-[var(--brand)] text-sm font-semibold text-white shadow-sm shadow-[var(--brand)]/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-[var(--brand-dark)]"
          >
            Sign In
            <ArrowRight className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-2xl border border-[var(--border)] text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-slate-50"
          >
            <KeyRound className="h-4 w-4" />
            Reset Password
          </button>
        </div>

        <div className="mt-5 rounded-2xl bg-slate-50 px-4 py-3 text-center">
          <p className="text-sm font-medium text-[var(--text-primary)]">Forgot your password?</p>
          <p className="text-xs text-[var(--text-secondary)]">Reset it in less than a minute.</p>
        </div>
      </div>
    </div>
  );
}
