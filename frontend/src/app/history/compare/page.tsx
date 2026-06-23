import { Suspense } from "react";
import CompareContent from "./CompareContent";

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4">
          <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
          <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
          <div className="h-48 animate-pulse rounded-2xl bg-slate-100" />
        </div>
      }
    >
      <CompareContent />
    </Suspense>
  );
}
