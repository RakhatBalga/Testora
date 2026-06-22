import { HTMLAttributes } from "react";

export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-200/50 ${className}`}
      {...props}
    />
  );
}
