"use client";

import { create } from "zustand";
import { api } from "@/lib/api";

export interface SourceChunk {
  text: string;
  filename: string;
  page: number;
  score?: number;
  confidence?: number;
}

export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceChunk[];
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
}

type Setter<T> = T | ((prev: T) => T);

interface ChatStore {
  messages: ChatMsg[];
  input: string;
  streaming: boolean;
  isTyping: boolean;
  historyLoading: boolean;
  sessions: ChatSession[];
  activeSessionId: string | null;
  setMessages: (value: Setter<ChatMsg[]>) => void;
  setInput: (value: Setter<string>) => void;
  setStreaming: (value: Setter<boolean>) => void;
  setIsTyping: (value: Setter<boolean>) => void;
  setHistoryLoading: (value: Setter<boolean>) => void;
  setSessions: (value: Setter<ChatSession[]>) => void;
  setActiveSessionId: (value: Setter<string | null>) => void;
  fetchSessions: () => Promise<void>;
  createSession: (title: string) => Promise<string>;
  renameSession: (id: string, title: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  fetchSessionHistory: (id: string) => Promise<void>;
  resetChat: () => void;
}

const resolveValue = <T,>(value: Setter<T>, current: T): T =>
  typeof value === "function" ? (value as (prev: T) => T)(current) : value;

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  input: "",
  streaming: false,
  isTyping: false,
  historyLoading: false,
  sessions: [],
  activeSessionId: null,

  setMessages(value) {
    set((state) => ({ messages: resolveValue(value, state.messages) }));
  },

  setInput(value) {
    set((state) => ({ input: resolveValue(value, state.input) }));
  },

  setStreaming(value) {
    set((state) => ({ streaming: resolveValue(value, state.streaming) }));
  },

  setIsTyping(value) {
    set((state) => ({ isTyping: resolveValue(value, state.isTyping) }));
  },

  setHistoryLoading(value) {
    set((state) => ({ historyLoading: resolveValue(value, state.historyLoading) }));
  },

  setSessions(value) {
    set((state) => ({ sessions: resolveValue(value, state.sessions) }));
  },

  setActiveSessionId(value) {
    set((state) => ({ activeSessionId: resolveValue(value, state.activeSessionId) }));
  },

  async fetchSessions() {
    try {
      const data = await api.get<ChatSession[]>("/api/v1/chat/sessions");
      set({ sessions: data });
      if (data.length > 0 && !get().activeSessionId) {
        set({ activeSessionId: data[0].id });
        await get().fetchSessionHistory(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch chat sessions:", err);
    }
  },

  async createSession(title) {
    try {
      const session = await api.post<ChatSession>("/api/v1/chat/sessions", { title });
      set((state) => ({
        sessions: [session, ...state.sessions],
        activeSessionId: session.id,
        messages: [],
      }));
      return session.id;
    } catch (err) {
      console.error("Failed to create chat session:", err);
      throw err;
    }
  },

  async renameSession(id, title) {
    try {
      const updated = await api.put<ChatSession>(`/api/v1/chat/sessions/${id}`, { title });
      set((state) => ({
        sessions: state.sessions.map((s) => (s.id === id ? updated : s)),
      }));
    } catch (err) {
      console.error("Failed to rename chat session:", err);
      throw err;
    }
  },

  async deleteSession(id) {
    try {
      await api.delete(`/api/v1/chat/sessions/${id}`);
      set((state) => {
        const nextSessions = state.sessions.filter((s) => s.id !== id);
        let nextActiveId = state.activeSessionId;
        if (state.activeSessionId === id) {
          nextActiveId = nextSessions.length > 0 ? nextSessions[0].id : null;
        }
        return {
          sessions: nextSessions,
          activeSessionId: nextActiveId,
        };
      });
      const activeId = get().activeSessionId;
      if (activeId) {
        await get().fetchSessionHistory(activeId);
      } else {
        set({ messages: [] });
      }
    } catch (err) {
      console.error("Failed to delete chat session:", err);
      throw err;
    }
  },

  async fetchSessionHistory(id) {
    set({ historyLoading: true });
    try {
      const data = await api.get<{ messages: ChatMsg[] }>(`/api/v1/chat/history/session/${id}`);
      set({ messages: data.messages });
    } catch (err) {
      console.error("Failed to fetch session history:", err);
    } finally {
      set({ historyLoading: false });
    }
  },

  resetChat() {
    set({
      messages: [],
      input: "",
      streaming: false,
      isTyping: false,
      historyLoading: false,
      sessions: [],
      activeSessionId: null,
    });
  },
}));
