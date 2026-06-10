import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, API_BASE, CONNECTION_ERROR_MESSAGE } from '../api';

describe('ApiClient', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let localStorageStore: Record<string, string> = {};

  beforeEach(() => {
    fetchMock = vi.fn();
    global.fetch = fetchMock as any;

    localStorageStore = {};
    const mockLocalStorage = {
      getItem: vi.fn((key: string) => localStorageStore[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        localStorageStore[key] = value.toString();
      }),
      removeItem: vi.fn((key: string) => {
        delete localStorageStore[key];
      }),
      clear: vi.fn(() => {
        localStorageStore = {};
      }),
    };
    Object.defineProperty(global, 'window', {
      value: { localStorage: mockLocalStorage, dispatchEvent: vi.fn(), CustomEvent: class {} },
      writable: true,
    });
    Object.defineProperty(global, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Headers & Auth', () => {
    it('should include Authorization header if token exists in localStorage', async () => {
      localStorageStore['token'] = 'test-token';
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ ok: true })));
      
      await api.get('/test');
      
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/test`,
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          })
        })
      );
    });

    it('should NOT include Authorization header if token is missing', async () => {
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ ok: true })));
      
      await api.get('/test');
      
      const calls = fetchMock.mock.calls;
      const headers = calls[0][1].headers;
      expect(headers).not.toHaveProperty('Authorization');
    });
  });

  describe('Parameter Handling', () => {
    it('should stringify JSON bodies correctly in POST requests', async () => {
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ success: true })));
      const body = { document_id: '123', query: 'hello' };
      
      await api.post('/message', body);
      
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/message`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(body)
        })
      );
    });

    it('should handle FormData correctly in postForm without overriding Content-Type', async () => {
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ success: true })));
      const formData = new FormData();
      formData.append('file', new Blob(['test'], { type: 'text/plain' }), 'test.txt');
      
      await api.postForm('/upload', formData);
      
      const callArgs = fetchMock.mock.calls[0];
      const reqInit = callArgs[1];
      
      expect(reqInit.method).toBe('POST');
      expect(reqInit.body).toBe(formData);
      expect(reqInit.headers).not.toHaveProperty('Content-Type');
    });
  });

  describe('Error Handling', () => {
    it('should throw connection error message if fetch throws TypeError', async () => {
      fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'));
      
      await expect(api.get('/test')).rejects.toThrow(CONNECTION_ERROR_MESSAGE);
    });

    it('should throw parsed error message if response is not ok', async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Invalid document ID' }), {
          status: 400,
          statusText: 'Bad Request'
        })
      );
      
      await expect(api.get('/test')).rejects.toThrow('Invalid document ID');
    });

    it('should fallback to statusText if response has no JSON body', async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(null, {
          status: 500,
          statusText: 'Internal Server Error'
        })
      );
      
      await expect(api.get('/test')).rejects.toThrow('Internal Server Error');
    });
  });

  describe('Token Refresh', () => {
    it('should auto-refresh token on 401 response', async () => {
      localStorageStore['token'] = 'old-token';
      localStorageStore['refresh_token'] = 'refresh-token';
      
      // 1st request -> 401
      fetchMock.mockResolvedValueOnce(new Response(null, { status: 401 }));
      
      // Refresh request -> 200
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
        access_token: 'new-token'
      })));
      
      // Retry original request -> 200
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ data: 'success' })));
      
      const res = await api.get('/protected');
      
      expect(res).toEqual({ data: 'success' });
      expect(localStorageStore['token']).toBe('new-token');
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });
  });
});
