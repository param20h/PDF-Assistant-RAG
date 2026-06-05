"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { Brain } from "lucide-react";
import { api } from "@/lib/api";

interface SharedSource {
  text: string;
  filename: string;
  page: number;
  score: number;
  confidence: number;
}

interface SharedAnswer {
  id: string;
  content: string;
  created_at: string;
  sources: SharedSource[];
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

function ShareAnswerContent() {
  const searchParams = useSearchParams();
  const messageId = searchParams.get("message_id");
  const missingMessageId = !messageId;
  const [answer, setAnswer] = useState<SharedAnswer | null>(null);
  const [error, setError] = useState("");
  const loading = !error && !answer && !missingMessageId;

  useEffect(() => {
    if (missingMessageId) {
      return;
    }

    let cancelled = false;

    void api
      .get<SharedAnswer>(`/api/v1/chat/share/${messageId}`)
      .then((data) => {
        if (cancelled) return;
        setAnswer(data);
        setError("");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setAnswer(null);
        setError(err instanceof Error ? err.message : "Shared answer not found");
      });

    return () => {
      cancelled = true;
    };
  }, [messageId, missingMessageId]);

  if (missingMessageId) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="rounded-xl border border-border/50 bg-card/80 px-6 py-5 text-center">
          <p className="text-lg font-semibold mb-1">Shared answer unavailable</p>
          <p className="text-sm text-muted-foreground">This shared answer could not be found.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-sm text-muted-foreground">Loading shared answer...</div>
      </div>
    );
  }

  if (error || !answer) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="rounded-xl border border-border/50 bg-card/80 px-6 py-5 text-center">
          <p className="text-lg font-semibold mb-1">Shared answer unavailable</p>
          <p className="text-sm text-muted-foreground">{error || "This shared answer could not be found."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-10 bg-background text-foreground">
      <div className="max-w-3xl mx-auto">
        <div className="rounded-2xl border border-border/50 bg-card/80 backdrop-blur-sm p-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-primary/15 flex items-center justify-center">
              <Brain className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">Shared AI Answer</h1>
              <p className="text-sm text-muted-foreground">
                {new Date(answer.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="prose-chat text-sm">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={markdownComponents}
            >
              {answer.content}
            </ReactMarkdown>
          </div>

          {answer.sources.length > 0 && (
            <div className="mt-6 border-t border-border/50 pt-4">
              <h2 className="text-sm font-semibold mb-3">Sources</h2>
              <div className="space-y-2">
                {answer.sources.map((source, index) => (
                  <div
                    key={`${answer.id}-${index}`}
                    className="rounded-lg border border-border/50 bg-background/60 p-3"
                  >
                    <p className="text-xs font-medium mb-1">
                      {source.filename} • Page {source.page}
                    </p>
                    <p className="text-xs text-muted-foreground">{source.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ShareAnswerPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center px-4">
          <div className="text-sm text-muted-foreground">Loading shared answer...</div>
        </div>
      }
    >
      <ShareAnswerContent />
    </Suspense>
  );
}
