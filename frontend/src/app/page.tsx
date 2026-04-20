"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { FileText, MessageSquare, Brain, Shield, Zap, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse-glow w-12 h-12 rounded-full bg-primary/20" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Hero ────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        {/* Glow effect */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />

        <div className="relative z-10 text-center max-w-3xl mx-auto animate-fade-in-up">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-sm text-primary mb-8">
            <Brain className="w-4 h-4" />
            Enterprise Agentic RAG System
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6 leading-[1.1]">
            Chat with your{" "}
            <span className="bg-gradient-to-r from-primary to-[oklch(0.65_0.2_200)] bg-clip-text text-transparent">
              documents
            </span>{" "}
            intelligently
          </h1>

          <p className="text-lg text-muted-foreground max-w-xl mx-auto mb-10 leading-relaxed">
            Upload financial reports, legal contracts, or research papers and get
            accurate, cited insights powered by advanced AI retrieval.
          </p>

          <div className="flex gap-4 justify-center">
            <Link href="/register">
              <Button size="lg" className="px-8 text-base h-12">
                Get Started Free
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="px-8 text-base h-12">
                Sign In
              </Button>
            </Link>
          </div>
        </div>

        {/* ── Features Grid ────────────────────────── */}
        <div className="relative z-10 mt-24 w-full max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              icon: FileText,
              title: "Multi-Format Upload",
              desc: "PDF, DOCX, TXT, and Markdown with smart chunking",
            },
            {
              icon: Search,
              title: "Semantic Search",
              desc: "Two-stage retrieval with cross-encoder reranking",
            },
            {
              icon: MessageSquare,
              title: "Streaming Chat",
              desc: "Real-time AI responses with source citations",
            },
            {
              icon: Zap,
              title: "Instant Insights",
              desc: "Extract key facts, summaries, and data points",
            },
            {
              icon: Shield,
              title: "Data Isolation",
              desc: "Per-user vector collections for complete privacy",
            },
            {
              icon: Brain,
              title: "Open-Source LLMs",
              desc: "Powered by Mistral and HuggingFace ecosystem",
            },
          ].map((f, i) => (
            <div
              key={i}
              className="group p-5 rounded-xl border border-border/50 bg-card/50 backdrop-blur-sm hover:border-primary/30 hover:bg-card transition-all duration-300"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <f.icon className="w-5 h-5 text-primary mb-3 group-hover:scale-110 transition-transform" />
              <h3 className="font-semibold text-sm mb-1">{f.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Footer ──────────────────────────────────── */}
      <footer className="text-center py-6 text-xs text-muted-foreground border-t border-border/50">
        Built with FastAPI • LangChain • ChromaDB • HuggingFace • Next.js
      </footer>
    </div>
  );
}
