"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth";

export function useRequireAuth() {
  const { token, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !token) {
      router.replace("/login");
    }
  }, [ready, token, router]);

  return { token, ready };
}
