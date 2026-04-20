"use client";

import { useState, useRef, useEffect } from "react";
import type { DocInfo } from "@/app/dashboard/page";
import { api } from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import MessageBubble from "./MessageBubble";
import SourceCard from "./SourceCard";
import { Send, Loader2, Trash2, MessageSquare } from "lucide-react";

export interface SourceChunk {
  text: string;
  filename: string;
  page: number;
  score: number;
  confidence: number;
}

export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceChunk[];
  isStreaming?: boolean;
}

interface Props {
  activeDoc: DocInfo | null;
  onCitationClick: (page: number) => void;
}

export default function ChatPanel({ activeDoc, onCitationClick }: Props) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevDocId = useRef<string | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Load history on doc change
  useEffect(() => {
    if (!activeDoc || activeDoc.id === prevDocId.current) return;
    prevDocId.current = activeDoc.id;

    api
      .get<{ messages: Array<{ id: string; role: string; content: string; sources?: SourceChunk[] }> }>(
        `/api/v1/chat/history/${activeDoc.id}`
      )
      .then((data) => {
        setMessages(
          data.messages.map((m) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
            sources: m.sources || [],
          }))
        );
      })
      .catch(() => setMessages([]));
  }, [activeDoc]);

  const handleSend = async () => {
    if (!input.trim() || streaming) return;

    const question = input.trim();
    setInput("");

    // Add user message
    const userMsg: ChatMsg = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      sources: [],
    };
    setMessages((prev) => [...prev, userMsg]);

    // Add placeholder assistant message
    const assistantId = `assistant-${Date.now()}`;
    const assistantMsg: ChatMsg = {
      id: assistantId,
      role: "assistant",
      content: "",
      sources: [],
      isStreaming: true,
    };
    setMessages((prev) => [...prev, assistantMsg]);
    setStreaming(true);

    try {
      const stream = api.streamPost("/api/v1/chat/ask/stream", {
        question,
        document_id: activeDoc?.id || null,
      });

      for await (const event of stream) {
        if (event.type === "token") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + (event.data as string) }
                : m
            )
          );
        } else if (event.type === "sources") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, sources: event.data as SourceChunk[] }
                : m
            )
          );
        } else if (event.type === "error") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: `Error: ${event.data}`, isStreaming: false }
                : m
            )
          );
        } else if (event.type === "done") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m
            )
          );
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: `Failed to get response: ${err instanceof Error ? err.message : "Unknown error"}`,
                isStreaming: false,
              }
            : m
        )
      );
    } finally {
      setStreaming(false);
    }
  };

  const handleClear = async () => {
    if (!activeDoc || !confirm("Clear all chat history for this document?")) return;
    try {
      await api.delete(`/api/v1/chat/history/${activeDoc.id}`);
      setMessages([]);
    } catch {
      // silently fail
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* ── Chat Messages ──────────────────────────── */}
      <ScrollArea className="flex-1 px-4" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <MessageSquare className="w-8 h-8 text-primary/60" />
            </div>
            <h3 className="text-lg font-semibold mb-1">
              {activeDoc ? "Ask about your document" : "Select a document"}
            </h3>
            <p className="text-sm text-muted-foreground text-center max-w-sm">
              {activeDoc
                ? `"${activeDoc.original_name}" is ready. Ask any question and get cited answers.`
                : "Upload and select a document from the sidebar to start chatting."}
            </p>
          </div>
        ) : (
          <div className="py-4 space-y-1 max-w-3xl mx-auto">
            {messages.map((msg) => (
              <div key={msg.id}>
                <MessageBubble message={msg} />
                {msg.role === "assistant" && msg.sources.length > 0 && (
                  <div className="ml-10 mt-1 mb-3">
                    <SourceCard sources={msg.sources} onPageClick={onCitationClick} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* ── Input Area ─────────────────────────────── */}
      <div className="border-t border-border/50 p-4 bg-card/30 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <Textarea
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              activeDoc
                ? `Ask about "${activeDoc.original_name}"...`
                : "Select a document first..."
            }
            disabled={streaming}
            className="min-h-[44px] max-h-32 resize-none bg-background/50 border-border/50"
            rows={1}
          />
          <div className="flex gap-1.5 shrink-0">
            <Button
              id="send-btn"
              size="icon"
              onClick={handleSend}
              disabled={!input.trim() || streaming}
              className="h-[44px] w-[44px]"
            >
              {streaming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClear}
                className="h-[44px] w-[44px] text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
