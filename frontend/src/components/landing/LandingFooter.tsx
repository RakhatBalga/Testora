"use client";

import Link from "next/link";
import { Mail } from "lucide-react";

const COLS = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "#features" },
      { label: "Tests", href: "#showcase" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#showcase" },
      { label: "Contact", href: "#contact" },
    ],
  },
];

export default function LandingFooter() {
  return (
    <footer id="contact" className="scroll-mt-24 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-5 py-16">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr_1fr]">
          {/* Brand */}
          <div>
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand)] text-sm font-bold text-white shadow-md">
                T
              </span>
              <span className="text-lg font-bold tracking-tight text-slate-900">Testora</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-slate-600">
              IELTS Academic Reading practice with evidence-backed review, AI Writing feedback,
              and progress you can measure.
            </p>
            <a
              href="mailto:hello@testora.app"
              className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              <Mail className="h-4 w-4" />
              hello@testora.app
            </a>
          </div>

          {/* Link columns */}
          {COLS.map((col) => (
            <div key={col.title}>
              <h3 className="text-sm font-semibold text-slate-900">{col.title}</h3>
              <ul className="mt-4 space-y-3">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      className="text-sm text-slate-600 transition-colors hover:text-blue-600"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-slate-200 pt-8">
          <p className="text-sm text-slate-500">
            © {new Date().getFullYear()} Testora. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
