import { ImageResponse } from "next/og";

export const alt = "Testora — IELTS Practice with AI Feedback";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "linear-gradient(135deg, #1d4ed8, #2563eb 60%, #3b82f6)",
          color: "white",
        }}
      >
        <div style={{ fontSize: 40, opacity: 0.85 }}>Testora</div>
        <div style={{ fontSize: 76, fontWeight: 800, lineHeight: 1.1, marginTop: 24 }}>
          IELTS practice with instant AI feedback
        </div>
        <div style={{ fontSize: 32, opacity: 0.85, marginTop: 28 }}>
          Reading · Listening · Writing · Personal study plan
        </div>
      </div>
    ),
    size,
  );
}
