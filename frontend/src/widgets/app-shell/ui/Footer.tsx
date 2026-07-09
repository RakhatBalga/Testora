import Image from "next/image";

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200/70 bg-white/60">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row">
        <div className="flex items-center gap-2">
          <Image
            src="/logo.svg"
            alt="Testora"
            width={28}
            height={28}
            className="h-7 w-7 object-contain"
          />
          <span className="text-sm text-slate-500">
            Testora — your AI IELTS coach
          </span>
        </div>
        <p className="text-sm text-slate-400">
          © {new Date().getFullYear()} Testora. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
