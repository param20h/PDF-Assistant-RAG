"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

interface User {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Lazy initializer reads localStorage once — avoids setState-in-effect lint error
  const [token, setToken] = useState<string | null>(
    () => (typeof window !== "undefined" ? localStorage.getItem("token") : null)
  );
  // loading=true only when a token exists and needs server validation.
  // If there's no token we're already done — no effect setState needed.
  const [loading, setLoading] = useState<boolean>(
    () => typeof window !== "undefined" && !!localStorage.getItem("token")
  );

  // ── Validate saved token on mount ─────────────────
  // NOTE: no synchronous setState here — setLoading/setUser/setToken are
  // only called inside async callbacks (.then / .catch / .finally).
  useEffect(() => {
    if (!token) return; // loading is already false when token is null
    api
      .get<User>("/api/v1/auth/me", { token })
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        setToken(null);
      })
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally runs once on mount only

  // ── Listen for token refresh events from ApiClient ──
  // When the API client auto-refreshes tokens, it dispatches custom events
  // so this context stays in sync without prop drilling.
  useEffect(() => {
    const handleTokensRefreshed = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.accessToken) {
        setToken(detail.accessToken);
      }
      if (detail?.user) {
        setUser(detail.user);
      }
    };

    const handleLoggedOut = () => {
      setToken(null);
      setUser(null);
    };

    window.addEventListener("auth:tokens-refreshed", handleTokensRefreshed);
    window.addEventListener("auth:logged-out", handleLoggedOut);

    return () => {
      window.removeEventListener("auth:tokens-refreshed", handleTokensRefreshed);
      window.removeEventListener("auth:logged-out", handleLoggedOut);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<{ access_token: string; refresh_token: string; user: User }>(
      "/api/v1/auth/login",
      { email, password }
    );
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const data = await api.post<{ access_token: string; refresh_token: string; user: User }>(
      "/api/v1/auth/google",
      { id_token: idToken }
    );
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    const data = await api.post<{ access_token: string; refresh_token: string; user: User }>(
      "/api/v1/auth/register",
      { username, email, password }
    );
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, loginWithGoogle, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
