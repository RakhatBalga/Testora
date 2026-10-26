"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth";
import { routes } from "@/shared/config";

export function useRequireAuth() {
  const { token, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !token) {
      const { pathname, search } = window.location;
      router.replace(`${routes.login()}?next=${encodeURIComponent(pathname + search)}`);
    }
  }, [ready, token, router]);

  return { token, ready };
}
