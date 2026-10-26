import type { Metadata } from "next";
import { PublicLanding } from "@/widgets/landing";
import { HomeGate } from "./HomeGate";

export const metadata: Metadata = {
  title: { absolute: "Testora — IELTS Practice with AI Feedback" },
  alternates: { canonical: "/" },
};

export default function HomeRoute() {
  return <HomeGate landing={<PublicLanding />} />;
}
