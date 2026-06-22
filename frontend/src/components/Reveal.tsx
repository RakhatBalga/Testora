"use client";

import { ReactNode, useEffect, useRef, useState } from "react";

type RevealProps = {
  children: ReactNode;
  /** Delay in ms before the reveal transition starts (for staggering). */
  delay?: number;
  className?: string;
};

/**
 * Fades + slides its children in when they scroll into view.
 * Respects prefers-reduced-motion via the .reveal CSS in globals.css.
 */
export function Reveal({ children, delay = 0, className = "" }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`reveal ${visible ? "reveal-visible" : ""} ${className}`}
    >
      {children}
    </div>
  );
}
