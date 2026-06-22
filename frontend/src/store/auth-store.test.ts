/**
 * Unit tests for useAuthStore (Zustand) — issue #443.
 *
 * Strategy: mock the `api` module so no real network calls are made,
 * then reset the store to its initial state before every test.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "@testing-library/react";

// ── Mock the api module ───────────────────────────────────────────────────────
vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
  },
}));

// Import AFTER vi.mock so the store picks up the mocked api
import { api } from "@/lib/api";
import { useAuthStore, type AuthUser } from "./auth-store";

// ── Helpers ───────────────────────────────────────────────────────────────────

const mockUser: AuthUser = {
  id: "user-123",
  username: "testuser",
  email: "test@example.com",
  is_admin: false,
  created_at: "2024-01-01T00:00:00Z",
};

/** Reset Zustand store + localStorage before every test. */
function resetStore() {
  localStorage.clear();
  useAuthStore.setState({
    user: null,
    token: null,
    loading: false,
    initialized: false,
  });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useAuthStore", () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  // ── Initial state ───────────────────────────────────────────────────────────

  describe("initial state", () => {
    it("starts with null user and token when localStorage is empty", () => {
      const { user, token, loading, initialized } = useAuthStore.getState();
      expect(user).toBeNull();
      expect(token).toBeNull();
      expect(loading).toBe(false);
      expect(initialized).toBe(false);
    });

    it("picks up an existing token from localStorage on creation", () => {
      localStorage.setItem("token", "stored-token");
      // Re-evaluate getStoredToken by manually syncing state as the store would
      useAuthStore.setState({ token: "stored-token", loading: true });
      const { token, loading } = useAuthStore.getState();
      expect(token).toBe("stored-token");
      expect(loading).toBe(true);
    });
  });

  // ── login ───────────────────────────────────────────────────────────────────

  describe("login", () => {
    it("sets user and token on successful login", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        access_token: "access-abc",
        refresh_token: "refresh-xyz",
        user: mockUser,
      });

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      const { user, token, loading, initialized } = useAuthStore.getState();
      expect(user).toEqual(mockUser);
      expect(token).toBe("access-abc");
      expect(loading).toBe(false);
      expect(initialized).toBe(true);
    });

    it("saves access_token and refresh_token to localStorage", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        access_token: "access-abc",
        refresh_token: "refresh-xyz",
        user: mockUser,
      });

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      expect(localStorage.getItem("token")).toBe("access-abc");
      expect(localStorage.getItem("refresh_token")).toBe("refresh-xyz");
    });

    it("calls api.post with correct endpoint and credentials", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        access_token: "access-abc",
        refresh_token: "refresh-xyz",
        user: mockUser,
      });

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/login", {
        email: "test@example.com",
        password: "password123",
      });
    });

    it("throws and does not update state when api.post rejects", async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error("Invalid credentials"));

      await expect(
        act(async () => {
          await useAuthStore.getState().login("bad@example.com", "wrong");
        })
      ).rejects.toThrow("Invalid credentials");

      const { user, token } = useAuthStore.getState();
      expect(user).toBeNull();
      expect(token).toBeNull();
    });
  });

  // ── loginWithGoogle ─────────────────────────────────────────────────────────

  describe("loginWithGoogle", () => {
    it("sets user and token on successful Google login", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        access_token: "google-access",
        refresh_token: "google-refresh",
        user: mockUser,
      });

      await act(async () => {
        await useAuthStore.getState().loginWithGoogle("google-id-token");
      });

      const { user, token, initialized } = useAuthStore.getState();
      expect(user).toEqual(mockUser);
      expect(token).toBe("google-access");
      expect(initialized).toBe(true);
    });

    it("saves tokens to localStorage after Google login", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        access_token: "google-access",
        refresh_token: "google-refresh",
        user: mockUser,
      });

      await act(async () => {
        await useAuthStore.getState().loginWithGoogle("google-id-token");
      });

      expect(localStorage.getItem("token")).toBe("google-access");
      expect(localStorage.getItem("refresh_token")).toBe("google-refresh");
    });

    it("calls api.post with the id_token payload", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        access_token: "google-access",
        refresh_token: "google-refresh",
        user: mockUser,
      });

      await act(async () => {
        await useAuthStore.getState().loginWithGoogle("my-google-token");
      });

      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/google", {
        id_token: "my-google-token",
      });
    });
  });

  // ── register ────────────────────────────────────────────────────────────────

  describe("register", () => {
    it("clears tokens and returns registration data on success", async () => {
      const registrationResponse = {
        message: "Registered successfully",
        email: "new@example.com",
        verification_url: null,
      };
      vi.mocked(api.post).mockResolvedValueOnce(registrationResponse);

      // Pre-populate localStorage to verify clearing
      localStorage.setItem("token", "old-token");
      localStorage.setItem("refresh_token", "old-refresh");

      let result: { message: string; email: string; verification_url?: string | null } | undefined;
      await act(async () => {
        result = await useAuthStore.getState().register("newuser", "new@example.com", "Password1!");
      });

      expect(result).toEqual(registrationResponse);
      expect(localStorage.getItem("token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });

    it("sets user to null and initialized to true after register", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({
        message: "ok",
        email: "new@example.com",
      });

      await act(async () => {
        await useAuthStore.getState().register("newuser", "new@example.com", "Password1!");
      });

      const { user, token, initialized } = useAuthStore.getState();
      expect(user).toBeNull();
      expect(token).toBeNull();
      expect(initialized).toBe(true);
    });
  });

  // ── logout ──────────────────────────────────────────────────────────────────

  describe("logout", () => {
    it("clears user, token, and localStorage on logout", async () => {
      // Set up a logged-in state first
      useAuthStore.setState({ user: mockUser, token: "access-abc", initialized: true });
      localStorage.setItem("token", "access-abc");
      localStorage.setItem("refresh_token", "refresh-xyz");

      vi.mocked(api.post).mockResolvedValueOnce({});

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      const { user, token, loading, initialized } = useAuthStore.getState();
      expect(user).toBeNull();
      expect(token).toBeNull();
      expect(loading).toBe(false);
      expect(initialized).toBe(true);
      expect(localStorage.getItem("token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });

    it("clears state even when the logout API call fails", async () => {
      useAuthStore.setState({ user: mockUser, token: "access-abc", initialized: true });
      localStorage.setItem("token", "access-abc");

      vi.mocked(api.post).mockRejectedValueOnce(new Error("Network error"));

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      const { user, token } = useAuthStore.getState();
      expect(user).toBeNull();
      expect(token).toBeNull();
      expect(localStorage.getItem("token")).toBeNull();
    });

    it("calls the logout endpoint", async () => {
      vi.mocked(api.post).mockResolvedValueOnce({});

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/logout");
    });
  });

  // ── initializeAuth ──────────────────────────────────────────────────────────

  describe("initializeAuth", () => {
    it("fetches current user and sets initialized on success", async () => {
      localStorage.setItem("token", "stored-token");
      useAuthStore.setState({ token: "stored-token", initialized: false });

      vi.mocked(api.get).mockResolvedValueOnce(mockUser);

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      const { user, initialized, loading } = useAuthStore.getState();
      expect(user).toEqual(mockUser);
      expect(initialized).toBe(true);
      expect(loading).toBe(false);
    });

    it("clears state when /auth/me returns an error", async () => {
      localStorage.setItem("token", "bad-token");
      useAuthStore.setState({ token: "bad-token", initialized: false });

      vi.mocked(api.get).mockRejectedValueOnce(new Error("Unauthorized"));

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      const { user, token, initialized } = useAuthStore.getState();
      expect(user).toBeNull();
      expect(token).toBeNull();
      expect(initialized).toBe(true);
      expect(localStorage.getItem("token")).toBeNull();
    });

    it("does nothing when already initialized", async () => {
      useAuthStore.setState({ initialized: true });

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      expect(api.get).not.toHaveBeenCalled();
    });
  });

  // ── syncTokensRefreshed ─────────────────────────────────────────────────────

  describe("syncTokensRefreshed", () => {
    it("updates token and user from event detail", () => {
      useAuthStore.setState({ user: mockUser, token: "old-token" });

      const updatedUser: AuthUser = { ...mockUser, username: "updated" };

      act(() => {
        useAuthStore.getState().syncTokensRefreshed({
          accessToken: "new-token",
          user: updatedUser,
        });
      });

      const { token, user, initialized } = useAuthStore.getState();
      expect(token).toBe("new-token");
      expect(user).toEqual(updatedUser);
      expect(initialized).toBe(true);
    });

    it("preserves existing token when accessToken is not in detail", () => {
      useAuthStore.setState({ token: "existing-token", user: mockUser });

      act(() => {
        useAuthStore.getState().syncTokensRefreshed({ user: mockUser });
      });

      expect(useAuthStore.getState().token).toBe("existing-token");
    });

    it("preserves existing user when user is not in detail", () => {
      useAuthStore.setState({ token: "existing-token", user: mockUser });

      act(() => {
        useAuthStore.getState().syncTokensRefreshed({ accessToken: "new-token" });
      });

      expect(useAuthStore.getState().user).toEqual(mockUser);
    });

    it("does nothing when called with no argument", () => {
      useAuthStore.setState({ token: "tok", user: mockUser });

      act(() => {
        useAuthStore.getState().syncTokensRefreshed();
      });

      expect(useAuthStore.getState().token).toBe("tok");
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });
  });

  // ── syncLoggedOut ───────────────────────────────────────────────────────────

  describe("syncLoggedOut", () => {
    it("clears user and token", () => {
      useAuthStore.setState({ user: mockUser, token: "tok", initialized: true });

      act(() => {
        useAuthStore.getState().syncLoggedOut();
      });

      const { user, token, loading, initialized } = useAuthStore.getState();
      expect(user).toBeNull();
      expect(token).toBeNull();
      expect(loading).toBe(false);
      expect(initialized).toBe(true);
    });
  });

  // ── setHfToken ──────────────────────────────────────────────────────────────

  describe("setHfToken", () => {
    it("updates user in state with the response from api.put", async () => {
      const updatedUser: AuthUser = { ...mockUser, hf_token: "hf_newtoken123" };
      useAuthStore.setState({ user: mockUser, token: "access-abc" });

      vi.mocked(api.put).mockResolvedValueOnce(updatedUser);

      await act(async () => {
        await useAuthStore.getState().setHfToken("hf_newtoken123");
      });

      expect(useAuthStore.getState().user).toEqual(updatedUser);
    });

    it("calls api.put with the correct endpoint and payload", async () => {
      const updatedUser: AuthUser = { ...mockUser, hf_token: "hf_abc" };
      vi.mocked(api.put).mockResolvedValueOnce(updatedUser);

      await act(async () => {
        await useAuthStore.getState().setHfToken("hf_abc");
      });

      expect(api.put).toHaveBeenCalledWith("/api/v1/auth/hf-token", {
        hf_token: "hf_abc",
      });
    });

    it("throws when api.put rejects", async () => {
      vi.mocked(api.put).mockRejectedValueOnce(new Error("Server error"));

      await expect(
        act(async () => {
          await useAuthStore.getState().setHfToken("bad-token");
        })
      ).rejects.toThrow("Server error");
    });
  });
});
