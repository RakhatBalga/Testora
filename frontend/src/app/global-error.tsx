"use client";

// Last-resort boundary: replaces the root layout, so it brings its own <html>.
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", padding: "4rem 1.5rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.5rem" }}>Something went wrong</h1>
        <p style={{ color: "#475569" }}>Testora hit an unexpected error.</p>
        <button
          type="button"
          onClick={reset}
          style={{ marginTop: "1rem", padding: "0.6rem 1.2rem", borderRadius: "0.75rem", border: 0, background: "#2563eb", color: "#fff", fontWeight: 600 }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
