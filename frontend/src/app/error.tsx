"use client";

import { ErrorState } from "@/shared/ui";

export default function RouteError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl py-16">
      <h1 className="mb-4 text-2xl font-extrabold tracking-tight text-slate-900">Something went wrong</h1>
      <ErrorState message="An unexpected error occurred while showing this page." onRetry={reset} />
    </div>
  );
}
