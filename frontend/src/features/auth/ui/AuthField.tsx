"use client";

import { InputHTMLAttributes, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
};

export function AuthField({ label, type = "text", className = "", id, ...props }: Props) {
  const inputId = id ?? props.name;
  const isPassword = type === "password";
  const [show, setShow] = useState(false);
  const effectiveType = isPassword && show ? "text" : type;

  return (
    <div>
      {/* visible label kept for accessibility; placeholder mirrors it */}
      <label htmlFor={inputId} className="sr-only">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type={effectiveType}
          placeholder={label}
          className={`h-[54px] w-full rounded-2xl border border-[var(--border)] bg-white px-4 text-[15px] text-[var(--text-primary)] outline-none transition placeholder:text-slate-400 focus:border-[var(--brand)] focus:ring-4 focus:ring-[var(--brand)]/12 ${
            isPassword ? "pr-12" : ""
          } ${className}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            aria-label={show ? "Hide password" : "Show password"}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 transition-colors hover:text-slate-600"
            tabIndex={-1}
          >
            {show ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
          </button>
        )}
      </div>
    </div>
  );
}
