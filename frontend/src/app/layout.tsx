import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/shared/auth";
import { Shell } from "@/widgets/app-shell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://testora.studio";
const DESCRIPTION =
  "Practice IELTS Academic Reading and Listening, and get instant AI feedback on your Writing with band scores and a personal study plan.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "Testora — IELTS Practice", template: "%s | Testora" },
  description: DESCRIPTION,
  applicationName: "Testora",
  icons: {
    icon: "/logo.svg",
    shortcut: "/logo.svg",
  },
  openGraph: {
    type: "website",
    siteName: "Testora",
    title: "Testora — IELTS Practice with AI Feedback",
    description: DESCRIPTION,
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Testora — IELTS Practice with AI Feedback",
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: "#2563eb",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <Shell>{children}</Shell>
        </AuthProvider>
      </body>
    </html>
  );
}
