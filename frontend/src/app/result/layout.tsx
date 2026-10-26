import type { Metadata } from "next";

export const metadata: Metadata = { title: "Reading result" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
