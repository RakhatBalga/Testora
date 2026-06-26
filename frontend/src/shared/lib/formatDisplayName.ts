export function formatDisplayName(username: string | null): string {
  const value = username?.trim().split("@")[0]?.replace(/[._-]+/g, " ");
  if (!value) return "there";

  return value
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
