import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export type User = { username: string; role: "admin" | "client"; allowedCells: string[] };
const AUTH_KEY = "superpaas_admin_auth";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  login: (u: string, p: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
  setUser: (u: User | null) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUserState] = useState<User | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(AUTH_KEY);
      if (raw) {
        const j = JSON.parse(raw);
        if (j.token && j.user) { setToken(j.token); setUserState(j.user); }
      }
    } catch { localStorage.removeItem(AUTH_KEY); }
  }, []);

  const login = async (username: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return { ok: false, error: (data as { message?: string }).message || "登录失败" };
    const { token: t, user: u } = data as { token: string; user: User };
    setToken(t); setUserState(u);
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token: t, user: u }));
    return { ok: true };
  };

  const logout = () => { setToken(null); setUserState(null); localStorage.removeItem(AUTH_KEY); };
  const setUser = (u: User | null) => setUserState(u);

  return (
    <AuthContext.Provider value={{ token, user, login, logout, setUser }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const c = useContext(AuthContext);
  if (!c) throw new Error("useAuth in AuthProvider");
  return c;
}
