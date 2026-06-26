export interface ProgressMovement {
  label: string;
  from: number | null;
  to: number | null;
  direction: "up" | "down" | "none";
}

export function greeting(d = new Date()): string {
  const h = d.getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}
