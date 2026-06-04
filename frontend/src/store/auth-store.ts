"use client";

import { create } from "zustand";
import { api } from "@/lib/api";

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  hf_token?: string;
  created_at: string;
}

interface AuthStore {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  initialized: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string
  ) => Promise<{ message: string; email: string; verification_url?: string | null }>;
  logout: () => void;
  initializeAuth: () => Promise<void>;
  syncTokensRefreshed: (detail?: { accessToken?: string; user?: AuthUser | null }) => void;
  syncLoggedOut: () => void;
  setHfToken: (hfToken: string) => Promise<void>;
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
    const data = await api.post<{ message: string; email: string; verification_url?: string | null }>(
      "/api/v1/auth/register",
      { username, email, password }
    );

    clearStoredTokens();
    set({
      token: null,
      user: null,
      loading: false,
      initialized: true,
    });
    return data;
  },

  async logout() {
    try {
      await api.post("/api/v1/auth/logout");
    } catch {
      // Ignore network errors on logout
    }
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
    set({ loading: true });

    try {
      const user = await api.get<AuthUser>(
        "/api/v1/auth/me",
        storedToken ? { token: storedToken } : undefined
      );
      set({
        user,
        token: storedToken || "cookie",
        loading: false,
        initialized: true,
      });
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

  async setHfToken(hfToken: string) {
    const response = await api.put<AuthUser>("/api/v1/auth/hf-token", { hf_token: hfToken });
    set({ user: response });
  },
}));
