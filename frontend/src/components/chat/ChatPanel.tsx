"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import type { DocInfo } from "@/app/dashboard/page";
import { api, API_BASE } from "@/lib/api";
import { useChatStore, type ChatMsg, type SourceBoundingBox, type SourceChunk } from "@/store/chat-store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import MessageBubble from "./MessageBubble";
import SourceCard from "./SourceCard";
import { Send, Loader2, Trash2, MessageSquare, Download, Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface ISpeechRecognitionEvent {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
      isFinal: boolean;
    };
  };
}

interface ISpeechRecognitionErrorEvent {
  error: string;
  message: string;
}

interface ISpeechRecognition {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: ISpeechRecognitionEvent) => void) | null;
  onerror: ((event: ISpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

interface WindowWithSpeech extends Window {
  SpeechRecognition?: new () => ISpeechRecognition;
  webkitSpeechRecognition?: new () => ISpeechRecognition;
}

interface CitationTarget {
  page: number;
  highlightRects?: SourceBoundingBox[];
}

interface Props {
  activeDoc: DocInfo | null;
  onCitationClick: (target: CitationTarget) => void;
}

export default function ChatPanel({ activeDoc, onCitationClick }: Props) {
  const { t, i18n } = useTranslation();
  const messages = useChatStore((state) => state.messages);
  const input = useChatStore((state) => state.input);
  const streaming = useChatStore((state) => state.streaming);
  const isTyping = useChatStore((state) => state.isTyping);
  const historyLoading = useChatStore((state) => state.historyLoading);
  const activeSessionId = useChatStore((state) => state.activeSessionId);
  const setMessages = useChatStore((state) => state.setMessages);
  const setInput = useChatStore((state) => state.setInput);
  const setStreaming = useChatStore((state) => state.setStreaming);
  const setIsTyping = useChatStore((state) => state.setIsTyping);
  const resetChat = useChatStore((state) => state.resetChat);
  const fetchSessionHistory = useChatStore((state) => state.fetchSessionHistory);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const recognitionRef = useRef<ISpeechRecognition | null>(null);
  const initialInputRef = useRef<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevDocId = useRef<string | null>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  const showEmptyState = messages.length === 0 && !isTyping && !historyLoading;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    const computedMaxHeight = Number.parseFloat(
      window.getComputedStyle(textarea).maxHeight
    );
    const maxHeight = Number.isFinite(computedMaxHeight)
      ? computedMaxHeight
      : textarea.scrollHeight;
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY =
      textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [input]);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      resetChat();
    };
  }, [resetChat]);

  // Load history on activeSessionId or fallback to activeDoc change
  useEffect(() => {
    if (activeSessionId) {
      fetchSessionHistory(activeSessionId);
      return;
    }

    if (!activeDoc) {
      prevDocId.current = null;
      setMessages([]);
      return;
    }

    if (activeDoc.id === prevDocId.current) return;

    const documentId = activeDoc.id;
    prevDocId.current = documentId;
    setMessages([]);
    let cancelled = false;

    api
      .get<{ messages: Array<{ id: string; role: string; content: string; sources?: SourceChunk[] }> }>(
        `/api/v1/chat/history/${documentId}`
      )
      .then((data) => {
        if (cancelled || prevDocId.current !== documentId) return;

        setMessages(
          data.messages.map((m) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
            sources: m.sources || [],
          }))
        );
      })
      .catch(() => {
        if (cancelled || prevDocId.current !== documentId) return;
        setMessages([]);
      });

    return () => {
      cancelled = true;
    };
  }, [activeSessionId, activeDoc, fetchSessionHistory, setMessages]);

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

    
    const assistantId = `assistant-${Date.now()}`;
    let assistantCreated = false;

    setStreaming(true);
    setIsTyping(true);

    try {
      const stream = api.streamPost("/api/v1/chat/ask/stream", {
        question,
        document_id: activeDoc?.id || null,
        session_id: activeSessionId,
      });

      for await (const event of stream) {
        if (event.type === "token") {
          // Create assistant message only when first token arrives
          if (!assistantCreated) {
            assistantCreated = true;
            setIsTyping(false);

            const assistantMsg: ChatMsg = {
              id: assistantId,
              role: "assistant",
              content: event.data as string,
              sources: [],
              isStreaming: true,
            };

            setMessages((prev) => [...prev, assistantMsg]);
          } else {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + (event.data as string) }
                  : m
              )
            );
          }
        } else if (event.type === "sources") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, sources: event.data as SourceChunk[] }
                : m
            )
          );
        } else if (event.type === "error") {
          setIsTyping(false);
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
      setIsTyping(false);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: t("chat.fallbackError", {
                  message: err instanceof Error ? err.message : "Unknown error",
                }),
                isStreaming: false,
              }
            : m
        )
      );
    } finally {
      setStreaming(false);
      setIsTyping(false);
    }
  };

  const handleClear = async () => {
    if (!activeDoc || !confirm(t("chat.clearConfirm"))) return;
    try {
      await api.delete(`/api/v1/chat/history/${activeDoc.id}`);
      setMessages([]);
    } catch {
        //silent fail
    }
  };

  const handleExport = (format: "md" | "txt" | "pdf") => {
    if (!activeDoc) return;
    setShowExportMenu(false);
    const token = localStorage.getItem("token");
    const url = `${API_BASE}/api/v1/chat/export/${activeDoc.id}?format=${format}&token=${token}`;
    // Trigger download via a temporary anchor
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // Close export dropdown on outside click
  useEffect(() => {
    if (!showExportMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showExportMenu]);

  // Cleanup speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const startRecording = () => {
    const SpeechRecognitionAPI =
      typeof window !== "undefined"
        ? (window as unknown as WindowWithSpeech).SpeechRecognition ||
          (window as unknown as WindowWithSpeech).webkitSpeechRecognition
        : null;

    if (!SpeechRecognitionAPI) {
      setSpeechError(t("chat.speechNotSupported", { defaultValue: "Speech recognition is not supported in this browser." }));
      return;
    }

    try {
      const recognition = new SpeechRecognitionAPI();
      recognition.continuous = true;
      recognition.interimResults = true;
      
      const currentLang = i18n.language || "en";
      const langMap: Record<string, string> = {
        en: "en-US",
        hi: "hi-IN",
        es: "es-ES",
        fr: "fr-FR",
      };
      recognition.lang = langMap[currentLang] || "en-US";

      initialInputRef.current = input;
      setSpeechError(null);
      setIsRecording(true);

      recognition.onresult = (event: ISpeechRecognitionEvent) => {
        let sessionTranscript = "";
        for (let i = 0; i < event.results.length; ++i) {
          sessionTranscript += event.results[i][0].transcript;
        }
        setInput(
          initialInputRef.current +
            (initialInputRef.current ? " " : "") +
            sessionTranscript.trim()
        );
      };

      recognition.onerror = (event: ISpeechRecognitionErrorEvent) => {
        const errorCode = event.error;
        if (errorCode === "aborted") return; // ignore manual aborts

        let msg = t("chat.speechError", { defaultValue: `Speech recognition error: ${errorCode}` });
        if (errorCode === "not-allowed") {
          msg = t("chat.micPermissionDenied", {
            defaultValue: "Microphone access denied. Please enable permissions in settings.",
          });
        } else if (errorCode === "no-speech") {
          msg = t("chat.noSpeechDetected", {
            defaultValue: "No speech was detected. Please try again.",
          });
        } else if (errorCode === "audio-capture") {
          msg = t("chat.audioCaptureError", {
            defaultValue: "No microphone found or microphone is not working.",
          });
        } else if (errorCode === "network") {
          msg = t("chat.networkError", {
            defaultValue: "Network error occurred during speech recognition.",
          });
        }
        setSpeechError(msg);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      setSpeechError(err instanceof Error ? err.message : "Failed to start speech recognition.");
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
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
      <div className="flex-1 px-4 overflow-y-auto custom-scrollbar" aria-busy={historyLoading}>
        {historyLoading ? (
          <div className="py-6 space-y-5 max-w-3xl mx-auto" aria-label="Loading chat history">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className={cn("flex gap-3", index % 2 === 0 ? "justify-end" : "justify-start")}
              >
                {index % 2 !== 0 && <Skeleton className="mt-1 h-8 w-8 rounded-full" />}
                <div className={cn("space-y-2", index % 2 === 0 ? "w-2/3" : "w-3/4")}>
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : showEmptyState ? (
          <div className="h-full flex flex-col items-center justify-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <MessageSquare className="w-8 h-8 text-primary/60" />
            </div>
            <h3 className="text-lg font-semibold mb-1">
              {activeDoc ? t("chat.askAboutDocument") : t("chat.selectDocument")}
            </h3>
            <p className="text-sm text-muted-foreground text-center max-w-sm">
              {activeDoc
                ? t("chat.readyPrompt", { name: activeDoc.original_name })
                : t("chat.uploadPrompt")}
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
            {isTyping && (
              <div className="flex items-center gap-1 ml-10 py-2">
                <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" />
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} className="h-4" />
      </div>

      {/* ── Input Area ─────────────────────────────── */}
      <div className="border-t border-border/50 p-4 bg-card/30 backdrop-blur-sm relative">
        <div className="max-w-3xl mx-auto relative">
          {/* Status / Error Message Area */}
          {(isRecording || speechError) && (
            <div className="absolute bottom-full mb-2 left-0 right-0 flex items-center justify-between bg-card border border-border/80 shadow-md rounded-lg px-3 py-1.5 text-xs animate-in fade-in slide-in-from-bottom-1 z-40 max-w-3xl mx-auto">
              <div className="flex items-center gap-2">
                {isRecording ? (
                  <>
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                    </span>
                    <span className="font-medium text-muted-foreground">
                      {t("chat.listening", { defaultValue: "Listening... Speak now." })}
                    </span>
                  </>
                ) : (
                  <span className="text-destructive font-medium">{speechError}</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  if (isRecording) {
                    stopRecording();
                  } else {
                    setSpeechError(null);
                  }
                }}
                className="text-muted-foreground hover:text-foreground font-semibold px-1.5 py-0.5 rounded hover:bg-muted transition-colors"
              >
                {isRecording ? t("chat.stop", { defaultValue: "Stop" }) : "✕"}
              </button>
            </div>
          )}

          <div className="flex gap-2 items-end">
            <div className="relative flex-1 flex items-center">
              <Textarea
                ref={textareaRef}
                id="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  activeDoc
                    ? t("chat.askPlaceholder", { name: activeDoc.original_name })
                    : t("chat.selectPlaceholder")
                }
                disabled={streaming}
                className="min-h-[44px] max-h-32 resize-none bg-background/50 border-border/50 pr-10"
                rows={1}
              />
              <Button
                id="mic-btn"
                type="button"
                variant="ghost"
                size="icon"
                disabled={streaming}
                onClick={toggleRecording}
                className={cn(
                  "absolute right-2 bottom-1.5 h-7 w-7 rounded-md text-muted-foreground transition-all duration-200",
                  isRecording
                    ? "bg-red-500/20 text-red-500 hover:bg-red-500/30 hover:text-red-600 animate-pulse"
                    : "hover:text-primary hover:bg-accent"
                )}
                title={
                  isRecording
                    ? t("chat.stopRecording", { defaultValue: "Stop recording" })
                    : t("chat.startRecording", { defaultValue: "Start recording" })
                }
              >
                {isRecording ? (
                  <MicOff className="h-4 w-4" />
                ) : (
                  <Mic className="h-4 w-4" />
                )}
              </Button>
            </div>
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
              <>
                {/* Export dropdown */}
                <div className="relative" ref={exportMenuRef}>
                  <Button
                    id="export-chat-btn"
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowExportMenu((v) => !v)}
                    className="h-[44px] w-[44px] text-muted-foreground hover:text-primary"
                    title={t("chat.exportTitle")}
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                  {showExportMenu && (
                    <div className="absolute bottom-full mb-2 right-0 min-w-[160px] rounded-lg border border-border bg-popover p-1 shadow-lg animate-in fade-in slide-in-from-bottom-2 z-50">
                      <button
                        id="export-md-btn"
                        onClick={() => handleExport("md")}
                        className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
                      >
                        <span className="text-base">📝</span>
                        {t("chat.markdown")}
                      </button>
                      <button
                        id="export-txt-btn"
                        onClick={() => handleExport("txt")}
                        className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
                      >
                        <span className="text-base">📄</span>
                        {t("chat.plainText")}
                      </button>
                      <button
                        id="export-pdf-btn"
                        onClick={() => handleExport("pdf")}
                        className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
                      >
                        <span className="text-base">📕</span>
                        {t("chat.pdf")}
                      </button>
                    </div>
                  )}
                </div>
                {/* Clear history */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleClear}
                  className="h-[44px] w-[44px] text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  </div>
  );
}
