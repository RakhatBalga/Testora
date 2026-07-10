export interface ProgressMovement {
  label: string;
  from: number | null;
  to: number | null;
  direction: "up" | "down" | "none";
}
