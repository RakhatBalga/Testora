"use client";

import { motion } from "framer-motion";

/**
 * Soft CSS cloud clusters that drift slowly across a blue panel.
 * Pure divs (no images) so they inherit the brand palette and stay light.
 */
function Puff({ className }: { className: string }) {
  return <div className={`absolute rounded-full bg-white/90 ${className}`} />;
}

function CloudShape({ scale = 1 }: { scale?: number }) {
  return (
    <div className="relative" style={{ width: 180 * scale, height: 60 * scale }}>
      <Puff className="left-0 top-[35%] h-[55%] w-[42%] blur-[6px]" />
      <Puff className="left-[22%] top-0 h-[75%] w-[46%] blur-[7px]" />
      <Puff className="left-[48%] top-[22%] h-[65%] w-[46%] blur-[6px]" />
      <Puff className="left-[15%] top-[45%] h-[50%] w-[70%] blur-[8px]" />
    </div>
  );
}

type CloudSpec = {
  top: string;
  left?: string;
  right?: string;
  scale: number;
  opacity: number;
  duration: number;
  delay?: number;
};

const CLOUDS: CloudSpec[] = [
  { top: "8%", left: "4%", scale: 1.4, opacity: 0.9, duration: 14 },
  { top: "18%", right: "6%", scale: 1.1, opacity: 0.75, duration: 17, delay: 1.2 },
  { top: "58%", left: "10%", scale: 0.9, opacity: 0.6, duration: 19, delay: 0.6 },
  { top: "66%", right: "12%", scale: 1.3, opacity: 0.8, duration: 15, delay: 2 },
  { top: "38%", left: "44%", scale: 0.7, opacity: 0.45, duration: 21, delay: 3 },
];

export default function Clouds() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {CLOUDS.map((c, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={{ top: c.top, left: c.left, right: c.right, opacity: c.opacity }}
          animate={{ x: [0, 22, 0, -18, 0] }}
          transition={{ duration: c.duration, delay: c.delay ?? 0, repeat: Infinity, ease: "easeInOut" }}
        >
          <CloudShape scale={c.scale} />
        </motion.div>
      ))}
    </div>
  );
}
