"use client";

import React, { useEffect } from "react";
import { useAuthStore } from "@/store/auth-store";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const initializeAuth = useAuthStore((state) => state.initializeAuth);
  const syncTokensRefreshed = useAuthStore((state) => state.syncTokensRefreshed);
  const syncLoggedOut = useAuthStore((state) => state.syncLoggedOut);

  useEffect(() => {
    void initializeAuth();
  }, [initializeAuth]);

  useEffect(() => {
    const handleTokensRefreshed = (e: Event) => {
      syncTokensRefreshed((e as CustomEvent).detail);
    };

    const handleLoggedOut = () => {
      syncLoggedOut();
    };

    window.addEventListener("auth:tokens-refreshed", handleTokensRefreshed);
    window.addEventListener("auth:logged-out", handleLoggedOut);

    return () => {
      window.removeEventListener("auth:tokens-refreshed", handleTokensRefreshed);
      window.removeEventListener("auth:logged-out", handleLoggedOut);
    };
  }, [syncLoggedOut, syncTokensRefreshed]);

  return <>{children}</>;
}

export function useAuth() {
  return useAuthStore();
}
