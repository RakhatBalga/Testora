const AUTH_TOKEN_KEY = "testora.auth.token";
const AUTH_USERNAME_KEY = "testora.auth.username";
const LEGACY_TOKEN_KEY = "token";
const LEGACY_USERNAME_KEY = "username";

function browserSessionStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage;
}

export function getStoredAuthToken(): string | null {
  const storage = browserSessionStorage();
  if (!storage) return null;

  const token = storage.getItem(AUTH_TOKEN_KEY);
  if (token) return token;

  const legacy = localStorage.getItem(LEGACY_TOKEN_KEY);
  if (!legacy) return null;
  storage.setItem(AUTH_TOKEN_KEY, legacy);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  return legacy;
}

export function getStoredUsername(): string | null {
  const storage = browserSessionStorage();
  if (!storage) return null;

  const username = storage.getItem(AUTH_USERNAME_KEY);
  if (username) return username;

  const legacy = localStorage.getItem(LEGACY_USERNAME_KEY);
  if (!legacy) return null;
  storage.setItem(AUTH_USERNAME_KEY, legacy);
  localStorage.removeItem(LEGACY_USERNAME_KEY);
  return legacy;
}

export function storeAuth(token: string, username: string): void {
  const storage = browserSessionStorage();
  if (!storage) return;
  storage.setItem(AUTH_TOKEN_KEY, token);
  storage.setItem(AUTH_USERNAME_KEY, username);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(LEGACY_USERNAME_KEY);
}

export function clearStoredAuth(): void {
  const storage = browserSessionStorage();
  storage?.removeItem(AUTH_TOKEN_KEY);
  storage?.removeItem(AUTH_USERNAME_KEY);
  if (typeof window === "undefined") return;
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(LEGACY_USERNAME_KEY);
}
