"use client";

import { useState, useRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import type { ChatMsg } from "@/store/chat-store";
import { api } from "@/lib/api";
import { Brain, User, Copy, Check, Share2, Link2, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  message: ChatMsg;
}

const markdownComponents: Components = {
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-border/70">
      <table className="min-w-full border-collapse text-left text-sm">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-muted/60 text-foreground">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="border-b border-border/70 px-3 py-2 font-semibold">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-border/50 px-3 py-2 align-top">
      {children}
    </td>
  ),
  pre: ({ children }) => (
    <pre className="not-prose my-3 overflow-x-auto rounded-lg border border-border/70 bg-zinc-950 p-3 text-sm text-zinc-100">
      {children}
    </pre>
  ),
  code: ({ className, children, ...props }) => {
    const language = /language-(\w+)/.exec(className ?? "")?.[1];

    return (
      <code className={className} data-language={language} {...props}>
        {children}
      </code>
    );
  },
};

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [shared, setShared] = useState(false);
  const [shareFailed, setShareFailed] = useState(false);
  const copiedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sharedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCopy = async () => {
    if (!message.content) return;
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      if (copiedTimeoutRef.current) clearTimeout(copiedTimeoutRef.current);
      copiedTimeoutRef.current = setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const handleShare = async () => {
    if (!message.content || message.isStreaming) return;

    try {
      const data = await api.post<{ message_id: string; share_url: string }>(
        `/api/v1/chat/share/${message.id}`
      );
      await navigator.clipboard.writeText(`${window.location.origin}${data.share_url}`);
      setShared(true);
      setShareFailed(false);
      if (sharedTimeoutRef.current) clearTimeout(sharedTimeoutRef.current);
      sharedTimeoutRef.current = setTimeout(() => {
        setShared(false);
        setShareFailed(false);
      }, 2000);
    } catch {
      setShareFailed(true);
      setShared(false);
      if (sharedTimeoutRef.current) clearTimeout(sharedTimeoutRef.current);
      sharedTimeoutRef.current = setTimeout(() => {
        setShareFailed(false);
      }, 2000);
    }
  };

  return (
    <div
      className={`flex gap-3 py-3 animate-fade-in-up ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
          <Brain className="w-4 h-4 text-primary" />
        </div>
      )}

      <div
        className={`relative max-w-[80%] rounded-xl px-4 py-3 ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "group bg-card border border-border/50 rounded-bl-sm"
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            {message.content && (
              <>
                {!message.isStreaming && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    className={`absolute top-2 right-2 text-muted-foreground hover:text-foreground transition-opacity ${
                      shared || shareFailed
                        ? "opacity-100"
                        : "opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto"
                    }`}
                    onClick={handleShare}
                    aria-label={shared ? "Link copied" : shareFailed ? "Share failed" : "Share response"}
                  >
                    {shared ? (
                      <Link2 className="w-3.5 h-3.5 text-emerald-400" />
                    ) : shareFailed ? (
                      <X className="w-3.5 h-3.5 text-destructive" />
                    ) : (
                      <Share2 className="w-3.5 h-3.5" />
                    )}
                  </Button>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  className={`absolute top-2 right-9 text-muted-foreground hover:text-foreground transition-opacity ${
                    copied
                      ? "opacity-100"
                      : "opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto"
                  }`}
                  onClick={handleCopy}
                  aria-label={copied ? "Copied" : "Copy response"}
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </Button>
                {copied && (
                  <div 
                    className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-zinc-800 text-white text-xs rounded-md whitespace-nowrap opacity-100 transition-opacity pointer-events-none"
                    role="status"
                    aria-live="polite"
                  >
                    Copied!
                  </div>
                )}
              </>
            )}
            <div className={`prose-chat text-sm ${message.content ? "pr-14" : ""}`}>
              {message.content ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={markdownComponents}
                >
                  {message.content}
                </ReactMarkdown>
              ) : message.isStreaming ? (
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
                </div>
              ) : null}
              {message.isStreaming && message.content && (
                <span className="inline-block w-0.5 h-4 bg-primary/60 animate-pulse ml-0.5 align-text-bottom" />
              )}
            </div>
          </>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
    </div>
  );
}
