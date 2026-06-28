"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  FileText,
  MessageSquare,
  Brain,
  Shield,
  Zap,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import ContributorsPanel from "@/components/layout/ContributorsPanel";
import OpenSourceBadge from "@/components/layout/OpenSourceBadge";

// ─── Feature card data ───────────────────────────────────────────────────────
const FEATURES = [
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
];

// ─── Page ────────────────────────────────────────────────────────────────────
export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [hallOfFameOpen, setHallOfFameOpen] = useState(false);

  const docsUrl = (process.env.NEXT_PUBLIC_API_URL || "https://param20h-pdf-assit-rag.hf.space") + "/docs";

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse w-12 h-12 rounded-full bg-primary/20" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="relative flex-1 flex flex-col items-center justify-center overflow-hidden px-6 py-28">

        {/* Ambient glow — top-center */}
        <div
          aria-hidden
          className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2
                     w-[700px] h-[420px]
                     bg-primary/10 rounded-full blur-[120px]"
        />

        {/* Subtle secondary glow — bottom-right */}
        <div
          aria-hidden
          className="pointer-events-none absolute bottom-0 right-0
                     w-[400px] h-[300px]
                     bg-primary/5 rounded-full blur-[100px]"
        />

        {/* Fine grid overlay */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(hsl(var(--foreground)) 1px, transparent 1px)," +
              "linear-gradient(90deg, hsl(var(--foreground)) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />

        {/* ── Content ─────────────────────────────────────────────────────── */}
        <div className="relative z-10 text-center max-w-3xl mx-auto space-y-8 animate-fade-in-up">

          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
                          bg-primary/10 border border-primary/20
                          text-xs font-medium tracking-wide text-primary uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_6px_theme(colors.green.400)] animate-pulse" />
            Enterprise Agentic RAG System
          </div>

          {/* Headline */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.08]">
            Chat with your{" "}
            <span className="bg-gradient-to-r from-primary via-primary/80 to-primary/60
                             bg-clip-text text-transparent">
              documents
            </span>
            <br />
            <span className="text-foreground/80 font-semibold text-4xl sm:text-5xl lg:text-6xl">
              intelligently.
            </span>
          </h1>

          {/* Divider glow line */}
          <div className="mx-auto w-24 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

          {/* Sub-copy */}
          <p className="text-base sm:text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed font-light">
            Upload financial reports, legal contracts, or research papers and get
            accurate, <span className="text-foreground/70 font-normal">cited insights</span> powered
            by advanced AI retrieval.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap gap-3 justify-center pt-2">
            <Link href="/register">
              <Button
                size="lg"
                className="px-8 text-base h-12 shadow-lg shadow-primary/20
                           hover:shadow-primary/30 hover:-translate-y-0.5
                           transition-all duration-200"
              >
                Get Started Free
              </Button>
            </Link>

            <Link href="/login">
              <Button
                size="lg"
                variant="outline"
                className="px-8 text-base h-12
                           hover:-translate-y-0.5 transition-all duration-200"
              >
                Sign In
              </Button>
            </Link>

            <a
              href={docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open Developer API Swagger documentation"
            >
              <Button
                size="lg"
                variant="secondary"
                className="px-8 text-base h-12
                           hover:-translate-y-0.5 transition-all duration-200"
              >
                Developer API
              </Button>
            </a>
          </div>

          {/* Social proof strip */}
          <p className="text-xs text-muted-foreground/60 tracking-wide pt-1">
            No credit card required &nbsp;·&nbsp; Open-source &nbsp;·&nbsp; Self-hostable
          </p>
        </div>

        {/* ── Feature cards ────────────────────────────────────────────────── */}
        <div className="relative z-10 mt-20 w-full max-w-4xl mx-auto
                        grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {FEATURES.map(({ icon: Icon, title, desc }, i) => (
            <div
              key={title}
              className="group p-5 rounded-xl
                         border border-border/40 bg-card/40 backdrop-blur-sm
                         hover:border-primary/25 hover:bg-card/70
                         transition-all duration-300 ease-out
                         hover:-translate-y-0.5"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              {/* Icon with subtle glow on hover */}
              <div className="w-8 h-8 mb-4 rounded-lg bg-primary/10 flex items-center justify-center
                              group-hover:bg-primary/15 transition-colors duration-300">
                <Icon className="w-4 h-4 text-primary group-hover:scale-110 transition-transform duration-300" />
              </div>

              <h3 className="font-semibold text-sm mb-1.5 text-foreground">{title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-border/40 bg-card/10 backdrop-blur-sm mt-auto">
        <div className="max-w-6xl mx-auto px-6 py-10 md:py-16 grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand info */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center gap-2">
              <img src="/logo.jpg" alt="Logo" className="w-6 h-6 rounded-md object-cover" />
              <span className="font-semibold text-sm tracking-wide text-foreground">
                Document AI Analyst
              </span>
            </div>
            <p className="text-xs text-muted-foreground max-w-sm leading-relaxed">
              Enterprise Retrieval-Augmented Generation (RAG) platform. Analyze complex PDF documents and chat with intelligence.
            </p>
          </div>

          {/* Links column 1 */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Product</h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <Link href="/login" className="hover:text-foreground transition-colors">Sign In</Link>
              </li>
              <li>
                <Link href="/register" className="hover:text-foreground transition-colors">Create Account</Link>
              </li>
              <li>
                <a href={docsUrl} target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">Developer API</a>
              </li>
            </ul>
          </div>

          {/* Links column 2 */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Legal & Privacy</h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy Policy</Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-foreground transition-colors">Terms of Service</Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-6 py-6 border-t border-border/20 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-[11px] text-muted-foreground/60">
            &copy; {new Date().getFullYear()} Document AI Analyst. All rights reserved.
          </p>
          <p className="text-[11px] text-muted-foreground/50 flex flex-wrap items-center gap-1.5 justify-center">
            Built with
            {["FastAPI", "LangChain", "ChromaDB", "HuggingFace", "Next.js"].map((tech, i, arr) => (
              <span key={tech} className="flex items-center gap-1.5">
                <span className="text-muted-foreground/70">{tech}</span>
                {i < arr.length - 1 && <span className="text-muted-foreground/30">·</span>}
              </span>
            ))}
          </p>
        </div>
      </footer>

      {/* Hall of Fame modal */}
      {hallOfFameOpen && (
        <ContributorsPanel onClose={() => setHallOfFameOpen(false)} />
      )}

      {/* Floating open-source badge */}
      <OpenSourceBadge onOpenHallOfFame={() => setHallOfFameOpen(true)} />
    </div>
  );
}
