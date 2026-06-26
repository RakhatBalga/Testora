export default function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200/70 bg-white/60">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white">
            T
          </span>
          <span className="text-sm text-slate-500">
            Testora — modern IELTS practice platform
          </span>
        </div>
        <p className="text-sm text-slate-400">
          © {new Date().getFullYear()} Testora. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
