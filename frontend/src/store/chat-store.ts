"use client";

import { create } from "zustand";

export interface SourceBoundingBox {
  left: number;
  top: number;
  width: number;
  height: number;
  unit?: "percent" | "pixels" | "pdf";
}

export interface SourceChunk {
  text: string;
  filename: string;
  page: number;
  score: number;
  confidence: number;
  highlightRects?: SourceBoundingBox[];
}

export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceChunk[];
  isStreaming?: boolean;
}

type Setter<T> = T | ((prev: T) => T);

interface ChatStore {
  messages: ChatMsg[];
  input: string;
  streaming: boolean;
  isTyping: boolean;
  setMessages: (value: Setter<ChatMsg[]>) => void;
  setInput: (value: Setter<string>) => void;
  setStreaming: (value: Setter<boolean>) => void;
  setIsTyping: (value: Setter<boolean>) => void;
  resetChat: () => void;
}

const resolveValue = <T,>(value: Setter<T>, current: T): T =>
  typeof value === "function" ? (value as (prev: T) => T)(current) : value;

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  input: "",
  streaming: false,
  isTyping: false,

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

  resetChat() {
    set({
      messages: [],
      input: "",
      streaming: false,
      isTyping: false,
    });
  },
}));
