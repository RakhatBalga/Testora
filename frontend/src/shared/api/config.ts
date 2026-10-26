export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function mediaUrl(path: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}
