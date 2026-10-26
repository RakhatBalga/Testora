import { redirect } from "next/navigation";

// Legacy single-question exam UI was removed; old links land in the library.
export default function LegacyTestRedirectPage() {
  redirect("/tests/reading");
}
