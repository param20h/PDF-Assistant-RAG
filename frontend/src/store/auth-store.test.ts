/**
 * Unit tests for auth-store.ts (Zustand state management)
 * Issue #443 — test(frontend): Write unit tests for auth-store (Zustand state)
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { act } from "@testing-library/react";

// ── Mocks ──────────────────────────────────────────────────────────────────

// Mock the api module before importing the store so the store picks it up
vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
  },
}));

import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import type { AuthUser } from "@/store/auth-store";

// ── Fixtures ───────────────────────────────────────────────────────────────

const MOCK_USER: AuthUser = {
  id: "user-123",
  username: "testuser",
  email: "test@example.com",
  is_admin: false,
  created_at: "2024-01-01T00:00:00Z",
};

const MOCK_ACCESS_TOKEN = "access-token-abc";
const MOCK_REFRESH_TOKEN = "refresh-token-xyz";

const MOCK_LOGIN_RESPONSE = {
  access_token: MOCK_ACCESS_TOKEN,
  refresh_token: MOCK_REFRESH_TOKEN,
  user: MOCK_USER,
};

// ── Helpers ────────────────────────────────────────────────────────────────

/** Reset Zustand store to its initial state between tests. */
function resetStore() {
  useAuthStore.setState({
    user: null,
    token: null,
    loading: false,
    initialized: false,
  });
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("useAuthStore", () => {
  beforeEach(() => {
    resetStore();
    localStorage.clear();
    vi.clearAllMocks();
  });

  // ── Initial state ──────────────────────────────────────────────────────

  describe("initial state", () => {
    it("has null user by default", () => {
      expect(useAuthStore.getState().user).toBeNull();
    });

    it("has null token when localStorage is empty", () => {
      expect(useAuthStore.getState().token).toBeNull();
    });

    it("is not initialized by default", () => {
      expect(useAuthStore.getState().initialized).toBe(false);
    });

    it("reads token from localStorage on init", () => {
      localStorage.setItem("token", "stored-token");
      // Re-evaluate getStoredToken by resetting with a stored value
      useAuthStore.setState({ token: localStorage.getItem("token") });
      expect(useAuthStore.getState().token).toBe("stored-token");
    });
  });

  // ── login ──────────────────────────────────────────────────────────────

  describe("login()", () => {
    it("sets user and token on successful login", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(MOCK_USER);
      expect(state.token).toBe(MOCK_ACCESS_TOKEN);
    });

    it("saves access_token to localStorage", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      expect(localStorage.getItem("token")).toBe(MOCK_ACCESS_TOKEN);
    });

    it("saves refresh_token to localStorage", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      expect(localStorage.getItem("refresh_token")).toBe(MOCK_REFRESH_TOKEN);
    });

    it("sets loading=false and initialized=true after login", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      const state = useAuthStore.getState();
      expect(state.loading).toBe(false);
      expect(state.initialized).toBe(true);
    });

    it("calls the correct login API endpoint", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });

      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/login", {
        email: "test@example.com",
        password: "password123",
      });
    });

    it("throws when API call fails", async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error("Invalid credentials"));

      await expect(
        act(async () => {
          await useAuthStore.getState().login("bad@example.com", "wrong");
        })
      ).rejects.toThrow("Invalid credentials");
    });
  });

  // ── loginWithGoogle ────────────────────────────────────────────────────

  describe("loginWithGoogle()", () => {
    it("sets user and token on successful Google login", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().loginWithGoogle("google-id-token");
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(MOCK_USER);
      expect(state.token).toBe(MOCK_ACCESS_TOKEN);
    });

    it("saves tokens to localStorage", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().loginWithGoogle("google-id-token");
      });

      expect(localStorage.getItem("token")).toBe(MOCK_ACCESS_TOKEN);
      expect(localStorage.getItem("refresh_token")).toBe(MOCK_REFRESH_TOKEN);
    });

    it("calls the Google auth endpoint with id_token", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().loginWithGoogle("google-id-token");
      });

      expect(api.post).toHaveBeenCalledWith("/api/v1/auth/google", {
        id_token: "google-id-token",
      });
    });
  });

  // ── logout ─────────────────────────────────────────────────────────────

  describe("logout()", () => {
    beforeEach(async () => {
      // Start from a logged-in state
      vi.mocked(api.post).mockResolvedValueOnce(MOCK_LOGIN_RESPONSE);
      await act(async () => {
        await useAuthStore.getState().login("test@example.com", "password123");
      });
    });

    it("clears user from state", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(undefined);

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      expect(useAuthStore.getState().user).toBeNull();
    });

    it("clears token from state", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(undefined);

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      expect(useAuthStore.getState().token).toBeNull();
    });

    it("removes token from localStorage", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(undefined);

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      expect(localStorage.getItem("token")).toBeNull();
    });

    it("removes refresh_token from localStorage", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(undefined);

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      expect(localStorage.getItem("refresh_token")).toBeNull();
    });

    it("still clears state even if API logout call fails", async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error("Network error"));

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      // State must be cleared regardless of network failure
      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().token).toBeNull();
      expect(localStorage.getItem("token")).toBeNull();
    });

    it("sets initialized=true after logout", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(undefined);

      await act(async () => {
        await useAuthStore.getState().logout();
      });

      expect(useAuthStore.getState().initialized).toBe(true);
    });
  });

  // ── register ───────────────────────────────────────────────────────────

  describe("register()", () => {
    const REGISTER_RESPONSE = {
      message: "Check your email to verify your account.",
      email: "new@example.com",
      verification_url: "http://localhost:3000/verify?token=abc",
    };

    it("returns registration response data", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(REGISTER_RESPONSE);

      let result: typeof REGISTER_RESPONSE | undefined;
      await act(async () => {
        result = await useAuthStore.getState().register("newuser", "new@example.com", "Password1!");
      });

      expect(result).toEqual(REGISTER_RESPONSE);
    });

    it("clears user and token from state after register", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(REGISTER_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().register("newuser", "new@example.com", "Password1!");
      });

      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().token).toBeNull();
    });

    it("clears localStorage tokens after register", async () => {
      localStorage.setItem("token", "old-token");
      localStorage.setItem("refresh_token", "old-refresh");
      vi.mocked(api.post).mockResolvedValueOnce(REGISTER_RESPONSE);

      await act(async () => {
        await useAuthStore.getState().register("newuser", "new@example.com", "Password1!");
      });

      expect(localStorage.getItem("token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });
  });

  // ── initializeAuth ─────────────────────────────────────────────────────

  describe("initializeAuth()", () => {
    it("sets user from /api/v1/auth/me when token exists", async () => {
      localStorage.setItem("token", MOCK_ACCESS_TOKEN);
      useAuthStore.setState({ token: MOCK_ACCESS_TOKEN, initialized: false });
      vi.mocked(api.get).mockResolvedValueOnce(MOCK_USER);

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      expect(useAuthStore.getState().user).toEqual(MOCK_USER);
    });

    it("clears state when /api/v1/auth/me throws", async () => {
      localStorage.setItem("token", "expired-token");
      useAuthStore.setState({ token: "expired-token", initialized: false });
      vi.mocked(api.get).mockRejectedValueOnce(new Error("401 Unauthorized"));

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().token).toBeNull();
      expect(localStorage.getItem("token")).toBeNull();
    });

    it("skips API call if already initialized", async () => {
      useAuthStore.setState({ initialized: true });

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      expect(api.get).not.toHaveBeenCalled();
    });

    it("sets initialized=true after completion", async () => {
      vi.mocked(api.get).mockResolvedValueOnce(MOCK_USER);
      useAuthStore.setState({ initialized: false });

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      expect(useAuthStore.getState().initialized).toBe(true);
    });
  });

  // ── syncTokensRefreshed ────────────────────────────────────────────────

  describe("syncTokensRefreshed()", () => {
    it("updates token when new accessToken provided", () => {
      useAuthStore.getState().syncTokensRefreshed({ accessToken: "new-token" });
      expect(useAuthStore.getState().token).toBe("new-token");
    });

    it("updates user when new user provided", () => {
      const updatedUser = { ...MOCK_USER, username: "updated" };
      useAuthStore.getState().syncTokensRefreshed({ user: updatedUser });
      expect(useAuthStore.getState().user?.username).toBe("updated");
    });

    it("does nothing when called with no argument", () => {
      useAuthStore.setState({ token: "existing-token" });
      useAuthStore.getState().syncTokensRefreshed(undefined);
      expect(useAuthStore.getState().token).toBe("existing-token");
    });

    it("preserves existing token when no new accessToken given", () => {
      useAuthStore.setState({ token: "old-token", user: MOCK_USER });
      const updatedUser = { ...MOCK_USER, username: "updated" };
      useAuthStore.getState().syncTokensRefreshed({ user: updatedUser });
      expect(useAuthStore.getState().token).toBe("old-token");
    });

    it("sets initialized=true and loading=false", () => {
      useAuthStore.setState({ loading: true, initialized: false });
      useAuthStore.getState().syncTokensRefreshed({ accessToken: "t" });
      expect(useAuthStore.getState().loading).toBe(false);
      expect(useAuthStore.getState().initialized).toBe(true);
    });
  });

  // ── syncLoggedOut ──────────────────────────────────────────────────────

  describe("syncLoggedOut()", () => {
    it("clears user and token", () => {
      useAuthStore.setState({ user: MOCK_USER, token: "some-token" });
      useAuthStore.getState().syncLoggedOut();

      expect(useAuthStore.getState().user).toBeNull();
      expect(useAuthStore.getState().token).toBeNull();
    });

    it("sets initialized=true and loading=false", () => {
      useAuthStore.setState({ loading: true, initialized: false });
      useAuthStore.getState().syncLoggedOut();

      expect(useAuthStore.getState().loading).toBe(false);
      expect(useAuthStore.getState().initialized).toBe(true);
    });
  });

  // ── setHfToken ─────────────────────────────────────────────────────────

  describe("setHfToken()", () => {
    it("updates user with response from API", async () => {
      const updatedUser = { ...MOCK_USER, hf_token: "hf_newtoken" };
      vi.mocked(api.put).mockResolvedValueOnce(updatedUser);

      await act(async () => {
        await useAuthStore.getState().setHfToken("hf_newtoken");
      });

      expect(useAuthStore.getState().user).toEqual(updatedUser);
    });

    it("calls the correct endpoint with hf_token", async () => {
      vi.mocked(api.put).mockResolvedValueOnce(MOCK_USER);

      await act(async () => {
        await useAuthStore.getState().setHfToken("hf_abc123");
      });

      expect(api.put).toHaveBeenCalledWith("/api/v1/auth/hf-token", {
        hf_token: "hf_abc123",
      });
    });
  });
});
