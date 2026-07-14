"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";

export type AuthUser = { id: number; email: string };
type AuthStatus = "loading" | "guest" | "authenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<AuthUser>("/api/auth/me")
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        setUser(null);
        setStatus("guest");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const me = await apiPost<AuthUser>("/api/auth/login", { email, password });
    setUser(me);
    setStatus("authenticated");
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const me = await apiPost<AuthUser>("/api/auth/signup", { email, password });
    setUser(me);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    await apiPost<void>("/api/auth/logout");
    setUser(null);
    setStatus("guest");
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
