import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { request, setUnauthorizedCallback, AUTH_KEY } from "@/api/request";

export type User = { username: string; role: "admin" | "client"; allowedCells: string[] };
const AUTH_KEY_REF = AUTH_KEY;

type AuthContextValue = {
  token: string | null;
  user: User | null;
  authChecked: boolean;
  login: (u: string, p: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function clearAuth(): void {
  localStorage.removeItem(AUTH_KEY_REF);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    setUnauthorizedCallback(() => {
      clearAuth();
      setToken(null);
      setUser(null);
      window.location.replace("/login");
    });
    return () => setUnauthorizedCallback(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const raw = localStorage.getItem(AUTH_KEY_REF);
    if (!raw) {
      setChecked(true);
      return;
    }
    try {
      const j = JSON.parse(raw);
      const t = j.token;
      const u = j.user;
      if (!t) {
        clearAuth();
        setChecked(true);
        return;
      }
      setToken(t);
      setUser(u ?? null);
      request<User>("/api/auth/me", { method: "GET" })
        .then((res) => {
          if (cancelled) return;
          if (!res.ok) {
            setToken(null);
            setUser(null);
            clearAuth();
            setChecked(true);
            return;
          }
          if (res.data && res.data.username) {
            setUser(res.data);
          }
          setChecked(true);
        })
        .catch(() => {
          if (!cancelled) {
            setToken(null);
            setUser(null);
            clearAuth();
          }
          setChecked(true);
        });
    } catch {
      clearAuth();
      setChecked(true);
    }
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await request<{ token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }, { skipAuth: true });
    if (!res.ok) return { ok: false, error: res.error || "登录失败" };
    const { token: t, user: u } = res.data!;
    setToken(t);
    setUser(u);
    localStorage.setItem(AUTH_KEY_REF, JSON.stringify({ token: t, user: u }));
    return { ok: true };
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    clearAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, authChecked: checked, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const c = useContext(AuthContext);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}
