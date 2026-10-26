import type { Metadata } from "next";

export const metadata: Metadata = { title: "Mistake notebook" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
