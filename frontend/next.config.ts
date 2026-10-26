import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";

// Origin of the backend API; the browser talks to it (fetch, media, avatars).
function apiOrigin(): string {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").origin;
  } catch {
    return "";
  }
}

const api = apiOrigin();

// Next injects inline bootstrap scripts, so script-src needs 'unsafe-inline'
// (no nonce pipeline here); 'unsafe-eval' is only for the dev server.
// Google sign-in is a full-page redirect, so it needs no extra CSP sources.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${api}`.trim(),
  `media-src 'self' blob: ${api}`.trim(),
  "font-src 'self' data:",
  `connect-src 'self' ${api}${isDev ? " ws: wss:" : ""}`.trim(),
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "object-src 'none'",
  "form-action 'self'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "microphone=(self), camera=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  // The legacy single-question exam UI was removed; old links go to the library.
  async redirects() {
    return [{ source: "/test/:id", destination: "/tests/reading", permanent: true }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
