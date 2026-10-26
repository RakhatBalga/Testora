"use client";

import { useEffect, useState } from "react";
import {
  api,
  type AttemptSummary,
  type SpeakingSubmissionSummary,
  type UserProfile,
  type WritingSubmissionSummary,
} from "@/shared/api";

/** Loads the profile and every graded submission list for the profile page. */
export function useProfileData(token: string | null) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [writing, setWriting] = useState<WritingSubmissionSummary[]>([]);
  const [speaking, setSpeaking] = useState<SpeakingSubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!token) return;
    let active = true;

    Promise.all([
      api.getProfile(),
      api.listAttempts(),
      api.listWritingSubmissions(),
      api.listSpeakingSubmissions(),
    ])
      .then(([p, a, w, s]) => {
        if (!active) return;
        setError("");
        setProfile(p);
        setAttempts(a);
        setWriting(w);
        setSpeaking(s);
      })
      .catch((err) => active && setError(err.message || "Profile failed to load."))
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [token, attempt]);

  const reload = () => {
    setLoading(true);
    setAttempt((n) => n + 1);
  };

  return { profile, setProfile, attempts, writing, speaking, loading, error, reload };
}
