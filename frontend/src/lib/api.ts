/**
 * API client for the FastAPI backend.
 * Handles authentication headers, base URL configuration,
 * and automatic token refresh on 401 responses.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const CONNECTION_ERROR_MESSAGE = "Could not connect to the server. Please try again later.";
const CONNECTION_ERROR_BANNER_MESSAGE = `⚠️ ${CONNECTION_ERROR_MESSAGE}`;

interface FetchOptions extends RequestInit {
  token?: string;
  /** Skip auto-refresh for this request (used internally for the refresh call itself) */
  _skipRefresh?: boolean;
}

class ApiClient {
  private baseUrl: string;
  /** Guards against multiple concurrent refresh attempts */
  private refreshPromise: Promise<string | null> | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  }

  private getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("refresh_token");
  }

  private getHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    const authToken = token || this.getToken();
    if (authToken && authToken !== "cookie") {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    return headers;
  }

  private async fetchWithConnectionError(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    try {
      const mergedInit = {
        credentials: "include" as const,
        ...init,
      };
      return await fetch(input, mergedInit);
    } catch (error) {
      if (error instanceof TypeError) {
        throw new Error(CONNECTION_ERROR_MESSAGE);
      }
      throw error;
    }
  }

  /**
   * Attempt to refresh the access token using the stored refresh token.
   * Uses a mutex so only one refresh happens at a time — concurrent
   * 401s all wait on the same promise.
   */
  private async tryRefreshToken(): Promise<string | null> {
    // If a refresh is already in-flight, wait for it
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return null;

    this.refreshPromise = (async () => {
      try {
        const res = await this.fetchWithConnectionError(`${this.baseUrl}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!res.ok) {
          // Refresh token is also expired/invalid — force logout
          this.clearTokens();
          return null;
        }

        const data = await res.json();
        // Store the new tokens
        localStorage.setItem("token", data.access_token);
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token);
        }

        // Dispatch a custom event so AuthProvider can update its state
        window.dispatchEvent(
          new CustomEvent("auth:tokens-refreshed", {
            detail: { accessToken: data.access_token, refreshToken: data.refresh_token, user: data.user },
          })
        );

        return data.access_token as string;
      } catch {
        this.clearTokens();
        return null;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  private clearTokens(): void {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    // Notify AuthProvider to update state
    window.dispatchEvent(new CustomEvent("auth:logged-out"));
  }

  private getPayloadMessage(payload: unknown): string | null {
    if (typeof payload === "string" && payload.trim()) {
      return payload;
    }

    if (Array.isArray(payload)) {
      const messages = payload
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
            return item.msg;
          }
          return null;
        })
        .filter((message): message is string => Boolean(message));

      return messages.length > 0 ? messages.join(", ") : null;
    }

    return null;
  }

  private async getErrorMessage(res: Response, fallback: string): Promise<string> {
    const payload = await res.json().catch(() => null);

    if (payload && typeof payload === "object") {
      const errorPayload = payload as { detail?: unknown; error?: unknown; message?: unknown };
      return (
        this.getPayloadMessage(errorPayload.detail) ||
        this.getPayloadMessage(errorPayload.message) ||
        this.getPayloadMessage(errorPayload.error) ||
        fallback
      );
    }

    return this.getPayloadMessage(payload) || fallback;
  }

  async get<T>(path: string, options?: FetchOptions): Promise<T> {
    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "GET",
      headers: this.getHeaders(options?.token),
      ...options,
    });

    // Auto-refresh on 401
    if (res.status === 401 && !options?._skipRefresh) {
      const newToken = await this.tryRefreshToken();
      if (newToken) {
        return this.get<T>(path, { ...options, token: newToken, _skipRefresh: true });
      }
    }

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Request failed"));
    }

    return res.json();
  }

  async post<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(options?.token),
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });

    // Auto-refresh on 401
    if (res.status === 401 && !options?._skipRefresh) {
      const newToken = await this.tryRefreshToken();
      if (newToken) {
        return this.post<T>(path, body, { ...options, token: newToken, _skipRefresh: true });
      }
    }

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Request failed"));
    }

    return res.json();
  }

  async put<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "PUT",
      headers: this.getHeaders(options?.token),
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });

    // Auto-refresh on 401
    if (res.status === 401 && !options?._skipRefresh) {
      const newToken = await this.tryRefreshToken();
      if (newToken) {
        return this.put<T>(path, body, { ...options, token: newToken, _skipRefresh: true });
      }
    }

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Request failed"));
    }

    return res.json();
  }

  async postForm<T>(path: string, formData: FormData, options?: FetchOptions): Promise<T> {
    const token = options?.token || this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    // Don't set Content-Type — browser sets multipart boundary automatically

    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: formData,
      ...options,
    });

    // Auto-refresh on 401
    if (res.status === 401 && !options?._skipRefresh) {
      const newToken = await this.tryRefreshToken();
      if (newToken) {
        return this.postForm<T>(path, formData, { ...options, token: newToken, _skipRefresh: true });
      }
    }

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Upload failed"));
    }

    return res.json();
  }

  async patch<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "PATCH",
      headers: this.getHeaders(options?.token),
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });

    if (res.status === 401 && !options?._skipRefresh) {
      const newToken = await this.tryRefreshToken();
      if (newToken) {
        return this.patch<T>(path, body, { ...options, token: newToken, _skipRefresh: true });
      }
    }

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Request failed"));
    }

    return res.json();
  }

  async delete<T>(path: string, options?: FetchOptions): Promise<T> {
    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: this.getHeaders(options?.token),
      ...options,
    });

    // Auto-refresh on 401
    if (res.status === 401 && !options?._skipRefresh) {
      const newToken = await this.tryRefreshToken();
      if (newToken) {
        return this.delete<T>(path, { ...options, token: newToken, _skipRefresh: true });
      }
    }

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Delete failed"));
    }

    return res.json();
  }

  /**
   * Stream a POST request as Server-Sent Events.
   * Yields parsed SSE data objects.
   */
  async *streamPost(path: string, body: unknown): AsyncGenerator<{ type: string; data?: unknown }> {
    let res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

    // Auto-refresh on 401
    if (res.status === 401) {
      const newToken = await this.tryRefreshToken();
      if (newToken) {
        res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
          method: "POST",
          headers: this.getHeaders(newToken),
          body: JSON.stringify(body),
        });
      }
    }

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Stream request failed"));
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            yield data;
          } catch {
            // Skip malformed lines
          }
        }
      }
    }
  }

  getPdfUrl(documentId: string): string {
    const token = this.getToken();
    return `${this.baseUrl}/api/v1/documents/${documentId}/pdf?token=${token}`;
  }
}

export const api = new ApiClient(API_BASE);
export { API_BASE, CONNECTION_ERROR_BANNER_MESSAGE, CONNECTION_ERROR_MESSAGE };
