/**
 * API client for the FastAPI backend.
 * Handles authentication headers and base URL configuration.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7860";

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

  async get<T>(path: string, options?: FetchOptions): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "GET",
      headers: this.getHeaders(options?.token),
      ...options,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || "Request failed");
    }

    return res.json();
  }

  async post<T>(path: string, body?: unknown, options?: FetchOptions): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(options?.token),
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || "Request failed");
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

    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: formData,
      ...options,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || "Upload failed");
    }

    return res.json();
  }

  async delete<T>(path: string, options?: FetchOptions): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: this.getHeaders(options?.token),
      ...options,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || "Delete failed");
    }

    return res.json();
  }

  /**
   * Stream a POST request as Server-Sent Events.
   * Yields parsed SSE data objects.
   */
  async *streamPost(path: string, body: unknown): AsyncGenerator<{ type: string; data?: unknown }> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || "Stream request failed");
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
export { API_BASE };
