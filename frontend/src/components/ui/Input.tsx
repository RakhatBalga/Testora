import { InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

export function Input({ label, className = "", id, ...props }: InputProps) {
  const inputId = id ?? props.name;
  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 ${className}`}
        {...props}
      />
    </div>
  );
}
