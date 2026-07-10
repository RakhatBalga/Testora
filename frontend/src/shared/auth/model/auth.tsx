"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  api,
  clearStoredAuth,
  getStoredAuthToken,
  getStoredUsername,
  storeAuth,
} from "@/shared/api";

type AuthContextType = {
  token: string | null;
  username: string | null;
  avatar: string | null;
  ready: boolean;
  login: (token: string, username: string) => void;
  logout: () => void;
  setAvatar: (avatar: string | null) => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [avatar, setAvatarState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setToken(getStoredAuthToken());
      setUsername(getStoredUsername());
      setReady(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  // Hydrate the uploaded avatar once we have a token. Best-effort: if the
  // profile call fails, the avatar just falls back to the initial. logout()
  // clears it, so there's no need to reset synchronously here when token is null.
  useEffect(() => {
    if (!token) return;
    let active = true;
    api
      .getProfile()
      .then((profile) => active && setAvatarState(profile.avatar))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [token]);

  const login = (newToken: string, newUsername: string) => {
    storeAuth(newToken, newUsername);
    setToken(newToken);
    setUsername(newUsername);
  };

  const logout = () => {
    clearStoredAuth();
    setToken(null);
    setUsername(null);
    setAvatarState(null);
  };

  return (
    <AuthContext.Provider
      value={{ token, username, avatar, ready, login, logout, setAvatar: setAvatarState }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
