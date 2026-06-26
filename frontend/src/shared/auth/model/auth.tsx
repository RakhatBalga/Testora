"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  clearStoredAuth,
  getStoredAuthToken,
  getStoredUsername,
  storeAuth,
} from "@/shared/api";

type AuthContextType = {
  token: string | null;
  username: string | null;
  ready: boolean;
  login: (token: string, username: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setToken(getStoredAuthToken());
      setUsername(getStoredUsername());
      setReady(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const login = (newToken: string, newUsername: string) => {
    storeAuth(newToken, newUsername);
    setToken(newToken);
    setUsername(newUsername);
  };

  const logout = () => {
    clearStoredAuth();
    setToken(null);
    setUsername(null);
  };

  return (
    <AuthContext.Provider value={{ token, username, ready, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
