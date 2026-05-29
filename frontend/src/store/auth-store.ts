"use client";

import { create } from "zustand";
import { api } from "@/lib/api";

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  created_at: string;
}

interface AuthStore {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  initialized: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  initializeAuth: () => Promise<void>;
  syncTokensRefreshed: (detail?: { accessToken?: string; user?: AuthUser | null }) => void;
  syncLoggedOut: () => void;
}

const getStoredToken = () =>
  typeof window !== "undefined" ? localStorage.getItem("token") : null;

const clearStoredTokens = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
};

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  token: getStoredToken(),
  loading: !!getStoredToken(),
  initialized: false,

  async login(email, password) {
    const data = await api.post<{ access_token: string; refresh_token: string; user: AuthUser }>(
      "/api/v1/auth/login",
      { email, password }
    );

    localStorage.setItem("token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    set({
      token: data.access_token,
      user: data.user,
      loading: false,
      initialized: true,
    });
  },

  async loginWithGoogle(idToken) {
    const data = await api.post<{ access_token: string; refresh_token: string; user: AuthUser }>(
      "/api/v1/auth/google",
      { id_token: idToken }
    );

    localStorage.setItem("token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    set({
      token: data.access_token,
      user: data.user,
      loading: false,
      initialized: true,
    });
  },

  async register(username, email, password) {
    const data = await api.post<{ access_token: string; refresh_token: string; user: AuthUser }>(
      "/api/v1/auth/register",
      { username, email, password }
    );

    localStorage.setItem("token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    set({
      token: data.access_token,
      user: data.user,
      loading: false,
      initialized: true,
    });
  },

  logout() {
    clearStoredTokens();
    set({
      token: null,
      user: null,
      loading: false,
      initialized: true,
    });
  },

  async initializeAuth() {
    const { initialized, token } = get();
    if (initialized) return;

    const storedToken = token ?? getStoredToken();
    if (!storedToken) {
      set({ token: null, user: null, loading: false, initialized: true });
      return;
    }

    set({ token: storedToken, loading: true });

    try {
      const user = await api.get<AuthUser>("/api/v1/auth/me", { token: storedToken });
      set({ user, token: storedToken, loading: false, initialized: true });
    } catch {
      clearStoredTokens();
      set({ user: null, token: null, loading: false, initialized: true });
    }
  },

  syncTokensRefreshed(detail) {
    if (!detail) return;

    set((state) => ({
      token: detail.accessToken ?? state.token,
      user: detail.user ?? state.user,
      loading: false,
      initialized: true,
    }));
  },

  syncLoggedOut() {
    set({
      token: null,
      user: null,
      loading: false,
      initialized: true,
    });
  },
}));
