"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, User, Users, Sparkles, Target, CalendarClock } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import AuthShell, { type AuthPanel } from "@/components/auth/AuthShell";
import { AuthField } from "@/components/auth/AuthField";
import AccountExistsModal from "@/components/auth/AccountExistsModal";

const TOTAL_STEPS = 4;

const GENDERS = [
  { value: "female", label: "Female", icon: User },
  { value: "male", label: "Male", icon: User },
  { value: "other", label: "Prefer not to say", icon: Users },
];

const TARGET_BANDS = [6.0, 6.5, 7.0, 7.5, 8.0];

function panelFor(step: number, name: string): AuthPanel {
  const first = name.trim().split(" ")[0];
  if (step === 1) {
    return {
      eyebrow: "Step 1 · Your name",
      title: "Let's personalize your learning journey.",
      subtitle: "A few quick questions so we can shape your IELTS prep around you.",
    };
  }
  if (step === 2) {
    return {
      eyebrow: first ? `Nice to meet you, ${first}` : "Step 2 · About you",
      title: "Help us adapt your preparation experience.",
      subtitle: "The more we know, the sharper your recommendations get.",
    };
  }
  if (step === 3) {
    return {
      eyebrow: first ? `What's the goal, ${first}?` : "Step 3 · Your goal",
      title: "Set your target band and exam date.",
      subtitle: "Your coach measures every gap and countdown against this goal.",
    };
  }
  return {
    eyebrow: first ? `Almost there, ${first}` : "Step 4 · Your account",
    title: "You're one step away from your IELTS goals.",
    subtitle: "Create your account and start practising with real feedback today.",
  };
}

export default function RegisterPage() {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [gender, setGender] = useState("");
  const [targetBand, setTargetBand] = useState<number | null>(null);
  const [examDate, setExamDate] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [accountExists, setAccountExists] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const back = () => {
    setError("");
    setStep((s) => Math.max(1, s - 1));
  };

  const next = () => {
    setError("");
    setStep((s) => Math.min(TOTAL_STEPS, s + 1));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // Only the account credentials are persisted; name/gender personalize the flow.
      await api.register(username, password);
      const res = await api.login(username, password);
      login(res.access_token, username);
      // Save the goal now that we're authenticated; don't block signup if it fails.
      if (targetBand != null) {
        try {
          await api.saveGoal({ target_band: targetBand, exam_date: examDate || null });
        } catch {
          // non-fatal — the user can set their goal later
        }
      }
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
    "inline-flex h-14 items-center justify-center gap-2 rounded-2xl bg-[var(--brand)] px-6 text-base font-semibold text-white shadow-sm shadow-[var(--brand)]/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-[var(--brand-dark)] hover:shadow-lg hover:shadow-[var(--brand)]/30 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-sm";
  const backBtn =
    "inline-flex h-14 items-center justify-center gap-2 rounded-2xl border border-[var(--border)] px-5 text-base font-semibold text-[var(--text-secondary)] transition-colors hover:border-slate-300 hover:bg-white";

  return (
    <AuthShell
      panel={panelFor(step, name)}
      progress={{ step, total: TOTAL_STEPS }}
      stepKey={step}
    >
      <div key={step} className="animate-fade-up">
        {error && (
          <p className="mb-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
        )}

        {/* Step 1 — name */}
        {step === 1 && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) next();
            }}
          >
            <p className="text-sm font-semibold uppercase tracking-wider text-[var(--brand)]">
              Welcome to Testora
            </p>
            <h1 className="mt-2 text-[2rem] font-extrabold tracking-tight text-[var(--text-primary)]">
              What should we call you?
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              This helps personalize your IELTS experience.
            </p>

            <div className="mt-8">
              <AuthField
                label="Your name"
                name="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                autoFocus
              />
            </div>

            <button type="submit" disabled={!name.trim()} className={`mt-8 w-full ${primaryBtn}`}>
              Continue
              <ArrowRight className="h-5 w-5" />
            </button>
          </form>
        )}

        {/* Step 2 — profile */}
        {step === 2 && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (gender) next();
            }}
          >
            <h1 className="text-[2rem] font-extrabold tracking-tight text-[var(--text-primary)]">
              Tell us about yourself
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              This information helps us tailor recommendations.
            </p>

            <div className="mt-8 grid grid-cols-3 gap-3">
              {GENDERS.map((g) => {
                const active = gender === g.value;
                return (
                  <button
                    key={g.value}
                    type="button"
                    onClick={() => setGender(g.value)}
                    className={`flex flex-col items-center gap-3 rounded-2xl border-2 px-3 py-6 text-center transition-all duration-200 ${
                      active
                        ? "border-[var(--brand)] bg-[var(--brand)]/[0.06] shadow-sm"
                        : "border-[var(--border)] bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <span
                      className={`flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
                        active
                          ? "bg-[var(--brand)] text-white"
                          : "bg-slate-100 text-[var(--text-secondary)]"
                      }`}
                    >
                      <g.icon className="h-6 w-6" />
                    </span>
                    <span
                      className={`text-sm font-semibold ${
                        active ? "text-[var(--brand)]" : "text-[var(--text-primary)]"
                      }`}
                    >
                      {g.label}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="mt-8 flex gap-3">
              <button type="button" onClick={back} className={backBtn}>
                <ArrowLeft className="h-5 w-5" />
                Back
              </button>
              <button type="submit" disabled={!gender} className={`flex-1 ${primaryBtn}`}>
                Continue
                <ArrowRight className="h-5 w-5" />
              </button>
            </div>
          </form>
        )}

        {/* Step 3 — goal */}
        {step === 3 && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (targetBand != null) next();
            }}
          >
            <h1 className="text-[2rem] font-extrabold tracking-tight text-[var(--text-primary)]">
              What band are you aiming for?
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              This is the target your coach works back from.
            </p>

            <div className="mt-8">
              <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-secondary)]">
                <Target className="h-4 w-4 text-[var(--brand)]" />
                Target band
              </p>
              <div className="grid grid-cols-5 gap-3">
                {TARGET_BANDS.map((b) => {
                  const active = targetBand === b;
                  return (
                    <button
                      key={b}
                      type="button"
                      onClick={() => setTargetBand(b)}
                      className={`flex items-center justify-center rounded-2xl border-2 py-4 text-base font-bold transition-all duration-200 ${
                        active
                          ? "border-[var(--brand)] bg-[var(--brand)]/[0.06] text-[var(--brand)] shadow-sm"
                          : "border-[var(--border)] bg-white text-[var(--text-primary)] hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      {b.toFixed(1)}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-7">
              <label
                htmlFor="examDate"
                className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text-secondary)]"
              >
                <CalendarClock className="h-4 w-4 text-[var(--brand)]" />
                Exam date <span className="font-normal text-slate-400">(optional)</span>
              </label>
              <input
                id="examDate"
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                className="h-14 w-full rounded-2xl border border-[var(--border)] bg-white px-4 text-base text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--brand)]"
              />
            </div>

            <div className="mt-8 flex gap-3">
              <button type="button" onClick={back} className={backBtn}>
                <ArrowLeft className="h-5 w-5" />
                Back
              </button>
              <button type="submit" disabled={targetBand == null} className={`flex-1 ${primaryBtn}`}>
                Continue
                <ArrowRight className="h-5 w-5" />
              </button>
            </div>
          </form>
        )}

        {/* Step 4 — account */}
        {step === 4 && (
          <form onSubmit={handleSubmit}>
            <h1 className="text-[2rem] font-extrabold tracking-tight text-[var(--text-primary)]">
              Create your account
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              Start preparing for your target IELTS score today.
            </p>

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

            <div className="mt-8 flex gap-3">
              <button type="button" onClick={back} className={backBtn}>
                <ArrowLeft className="h-5 w-5" />
                Back
              </button>
              <button
                type="submit"
                disabled={loading || !username || !password}
                className={`flex-1 ${primaryBtn}`}
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
            </div>
          </form>
        )}
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
