/**
 * API client for the FastAPI backend.
 * Handles authentication headers and base URL configuration.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const CONNECTION_ERROR_MESSAGE = "Could not connect to the server. Please try again later.";
const CONNECTION_ERROR_BANNER_MESSAGE = `⚠️ ${CONNECTION_ERROR_MESSAGE}`;

interface FetchOptions extends RequestInit {
  token?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  }

  private getHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    const authToken = token || this.getToken();
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    return headers;
  }

  private async fetchWithConnectionError(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    try {
      return await fetch(input, init);
    } catch (error) {
      if (error instanceof TypeError) {
        throw new Error(CONNECTION_ERROR_MESSAGE);
      }
      throw error;
    }
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

    if (!res.ok) {
      throw new Error(await this.getErrorMessage(res, res.statusText || "Upload failed"));
    }

    return res.json();
  }

  async delete<T>(path: string, options?: FetchOptions): Promise<T> {
    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: this.getHeaders(options?.token),
      ...options,
    });

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
    const res = await this.fetchWithConnectionError(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

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
