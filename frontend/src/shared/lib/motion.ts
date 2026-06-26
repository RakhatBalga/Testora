import type { Variants } from "framer-motion";

/** Smooth, slightly springy ease used across the landing page. */
export const EASE = [0.22, 1, 0.36, 1] as const;

/** Fade + rise. Use with `custom={index}` to stagger siblings. */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.08, ease: EASE },
  }),
};

/** Container that staggers its children on scroll into view. */
export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

/** Standard viewport config — animate once, a little before fully visible. */
export const viewport = { once: true, margin: "-80px" } as const;
