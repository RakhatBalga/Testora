"use client";

import Link from "next/link";
import { Mail, Send, AtSign, Globe, Briefcase } from "lucide-react";

const COLS = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "#features" },
      { label: "Tests", href: "#showcase" },
      { label: "Reviews", href: "#testimonials" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#showcase" },
      { label: "Blog", href: "#" },
      { label: "Careers", href: "#" },
      { label: "Contact", href: "#contact" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", href: "#" },
      { label: "Terms", href: "#" },
      { label: "Cookies", href: "#" },
    ],
  },
];

const SOCIALS = [
  { icon: Send, href: "#", label: "Telegram" },
  { icon: AtSign, href: "#", label: "Instagram" },
  { icon: Globe, href: "#", label: "Website" },
  { icon: Briefcase, href: "#", label: "LinkedIn" },
];

export default function LandingFooter() {
  return (
    <footer id="contact" className="scroll-mt-24 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-5 py-16">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          {/* Brand */}
          <div>
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold text-white shadow-md">
                T
              </span>
              <span className="text-lg font-bold tracking-tight text-slate-900">Testora</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-slate-600">
              The all-in-one IELTS practice platform. Realistic tests, instant AI feedback, and
              progress you can measure.
            </p>
            <a
              href="mailto:hello@testora.app"
              className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
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
                      className="text-sm text-slate-600 transition-colors hover:text-indigo-600"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-slate-200 pt-8 sm:flex-row">
          <p className="text-sm text-slate-500">
            © {new Date().getFullYear()} Testora. All rights reserved.
          </p>
          <div className="flex gap-2">
            {SOCIALS.map((s) => (
              <a
                key={s.label}
                href={s.href}
                aria-label={s.label}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition-all hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600"
              >
                <s.icon className="h-4 w-4" />
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
