import { API_URL } from "../config";
import { NetworkError, detailToMessage } from "../errors";
import { request, requestForm } from "../http";
import type { UserProfile, UserProfileUpdate } from "../types";

/** Cold Render needs ~45 s to wake; allow a generous margin for the first sign-in. */
export const LOGIN_TIMEOUT_MS = 90_000;

async function loginWithPassword(username: string, password: string) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), LOGIN_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
      signal: controller.signal,
    });
    if (res.status === 401) {
      throw new Error("Incorrect email, username or password.");
    }
    if (res.status === 502 || res.status === 503 || res.status === 504) {
      throw new NetworkError("unavailable");
    }
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      throw new Error(detailToMessage(data?.detail, "Sign-in failed. Please try again."));
    }
    return await res.json() as { access_token: string; token_type: string };
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error("Sign-in is taking too long. The server may still be waking up, so please try again in a moment.");
    }
    if (error instanceof TypeError) {
      throw new Error("Unable to connect. Check your connection and try again.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export const authApi = {
  register: (username: string, password: string, target_band = 7.5) =>
    request<{ message: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, target_band }),
    }, { timeoutMs: LOGIN_TIMEOUT_MS }),

  login: loginWithPassword,

  googleStart: (state: string, redirect_uri: string) =>
    request<{ authorization_url: string }>("/auth/google/start", {
      method: "POST",
      body: JSON.stringify({ state, redirect_uri }),
    }),

  googleAuth: (
    code: string,
    redirect_uri: string,
    state: string,
    signup?: { username?: string; target_band?: number }
  ) =>
    request<{ access_token: string; token_type: string; is_new_user: boolean; username: string }>(
      "/auth/google",
      {
        method: "POST",
        body: JSON.stringify({ ...signup, code, redirect_uri, state }),
      },
      { timeoutMs: LOGIN_TIMEOUT_MS }
    ),

  setUsername: (username: string) =>
    request<{ access_token: string; token_type: string }>("/auth/username", {
      method: "POST",
      body: JSON.stringify({ username }),
    }),

  getProfile: () => request<UserProfile>("/auth/me"),

  updateProfile: (update: number | UserProfileUpdate) =>
    request<UserProfile>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(typeof update === "number" ? { target_band: update } : update),
    }),

  uploadAvatar: (image: File) => {
    const formData = new FormData();
    formData.append("image", image, image.name);
    return requestForm<UserProfile>("/auth/me/avatar", formData);
  },

  deleteAvatar: () => request<UserProfile>("/auth/me/avatar", { method: "DELETE" }),
};
