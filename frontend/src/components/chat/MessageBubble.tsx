"use client";

import { useState, useRef, useEffect, useSyncExternalStore } from "react";
import { formatDistanceToNow } from "date-fns";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import type { ChatMsg } from "@/store/chat-store";
import { api } from "@/lib/api";
import { Brain, User, Copy, Check, Share2, Link2, X, Play, Pause, GitBranch, ChevronDown } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/store/chat-store";
import { useSettingsStore } from "@/store/settings-store";

const subscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

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
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showThoughts, setShowThoughts] = useState(false);

  useEffect(() => {
    if (message.isStreaming && message.thoughts && message.thoughts.length > 0) {
      setShowThoughts(true);
    }
  }, [message.isStreaming, message.thoughts]);
  const copiedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sharedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Component unmount ആകുമ്പോൾ speech cancel ചെയ്യും
 useEffect(() => {
  const currentUtterance = utteranceRef.current;

  return () => {
    if (currentUtterance) {
      window.speechSynthesis.cancel();
    }
  };
}, []);

 

const setCurrentBranchId = useChatStore(
  (s) => s.setCurrentBranchId
);

  const mounted = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const fontSize = useSettingsStore((s) => s.fontSize);

  const activeFontSize = mounted ? fontSize : "medium";
  const fontSizeClass = {
    small: "text-xs",
    medium: "text-sm",
    large: "text-base",
  }[activeFontSize];

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

  const handleSpeech = () => {
    if (!message.content || message.isStreaming) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      utteranceRef.current = null;
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message.content);
    utteranceRef.current = utterance;

    utterance.onend = () => {
      setIsSpeaking(false);
      utteranceRef.current = null;
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
      utteranceRef.current = null;
    };

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

const handleBranch = () => {
  setCurrentBranchId(message.id);

  console.log("Branch created from:", message.id);
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
          <p className={`leading-relaxed whitespace-pre-wrap ${fontSizeClass}`}>{message.content}</p>
        ) : (
          <>
            {message.content && (
              <>
                {/* Share button */}
                {!message.isStreaming && (
                  <Tooltip>
                    <TooltipTrigger
                      type="button"
                      className={cn(
                        buttonVariants({ variant: "ghost", size: "icon-xs" }),
                        `absolute top-2 right-2 text-muted-foreground hover:text-foreground transition-opacity ${
                          shared || shareFailed
                            ? "opacity-100"
                            : "opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto"
                        }`,
                      )}
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
                    </TooltipTrigger>
                    <TooltipContent>
                      {shared ? "Link copied" : shareFailed ? "Share failed" : "Share response"}
                    </TooltipContent>
                  </Tooltip>
                )}

                {/* Copy button */}
                <Tooltip>
                  <TooltipTrigger
                    type="button"
                    className={cn(
                      buttonVariants({ variant: "ghost", size: "icon-xs" }),
                      `absolute top-2 right-9 text-muted-foreground hover:text-foreground transition-opacity ${
                        copied
                          ? "opacity-100"
                          : "opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto"
                      }`,
                    )}
                    onClick={handleCopy}
                    aria-label={copied ? "Copied" : "Copy response"}
                  >
                    {copied ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </TooltipTrigger>
                  <TooltipContent>{copied ? "Copied" : "Copy response"}</TooltipContent>
                </Tooltip>

                {copied && (
                  <div
                    className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-zinc-800 text-white text-xs rounded-md whitespace-nowrap opacity-100 transition-opacity pointer-events-none"
                    role="status"
                    aria-live="polite"
                  >
                    Copied!
                  </div>
                )}

                {/* Speech button */}
                {!message.isStreaming && (
                  <Tooltip>
                    <TooltipTrigger
                      type="button"
                      className={cn(
                        buttonVariants({ variant: "ghost", size: "icon-xs" }),
                        `absolute top-2 right-16 text-muted-foreground hover:text-foreground transition-opacity ${
                          isSpeaking
                            ? "opacity-100"
                            : "opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto"
                        }`,
                      )}
                      onClick={handleSpeech}
                      aria-label={isSpeaking ? "Stop reading" : "Read response"}
                    >
                      {isSpeaking ? (
                        <Pause className="w-3.5 h-3.5" />
                      ) : (
                        <Play className="w-3.5 h-3.5" />
                      )}
                    </TooltipTrigger>
                    <TooltipContent>{isSpeaking ? "Stop reading" : "Read response"}</TooltipContent>
                  </Tooltip>
                )}

                {/* Branch button */}
                <Tooltip>
                  <TooltipTrigger
                    type="button"
                    className={cn(
                      buttonVariants({ variant: "ghost", size: "icon-xs" }),
                      "absolute top-2 right-24 text-muted-foreground hover:text-foreground transition-opacity opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto",
                    )}
                    onClick={handleBranch}
                    aria-label="Branch conversation"
                  >
                    <GitBranch className="w-3.5 h-3.5" />
                  </TooltipTrigger>
                  <TooltipContent>Branch conversation</TooltipContent>
                </Tooltip>
              </>
            )}

            {message.thoughts && message.thoughts.length > 0 && (
              <div className="mb-3 border border-border/60 rounded-lg bg-muted/40 overflow-hidden text-xs">
                <button
                  type="button"
                  onClick={() => setShowThoughts((prev) => !prev)}
                  className="w-full flex items-center justify-between px-3 py-2 text-muted-foreground hover:text-foreground font-medium transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <Brain className="w-3.5 h-3.5 animate-pulse text-primary" />
                    <span>{message.isStreaming ? "Thinking..." : "View reasoning steps"}</span>
                  </div>
                  <ChevronDown
                    className={cn(
                      "w-3.5 h-3.5 transition-transform duration-200",
                      showThoughts && "transform rotate-180"
                    )}
                  />
                </button>
                {showThoughts && (
                  <div className="px-3 pb-3 pt-1 border-t border-border/40 space-y-2 max-h-60 overflow-y-auto font-mono text-[11px] leading-relaxed text-muted-foreground">
                    {message.thoughts.map((thought, idx) => (
                      <div key={idx} className="whitespace-pre-wrap border-l-2 border-primary/30 pl-2">
                        {thought}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className={`prose-chat ${fontSizeClass} ${message.content ? "pr-20" : ""}`}>
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
        
         <div
          className={`text-xs text-muted-foreground mt-2 ${
            isUser ? "text-right" : "text-left"
          }`}
          title={new Date(Number(message.id.split("-")[1])).toLocaleString()}
        >
          {formatDistanceToNow(
            new Date(Number(message.id.split("-")[1])),
            { addSuffix: true }
          )}
        </div>
      </div>
       {isUser && (
        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
    </div>
  );
}
