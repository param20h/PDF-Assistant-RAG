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
  const [mounted, setMounted] = useState(false);
  const [hallOfFameOpen, setHallOfFameOpen] = useState(false);
  const [maintenanceVisible, setMaintenanceVisible] = useState(true);

  const docsUrl = (process.env.NEXT_PUBLIC_API_URL || "https://param20h-pdf-assit-rag.hf.space") + "/docs";

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && !loading && user) {
      router.replace("/dashboard");
    }
  }, [user, loading, router, mounted]);

  if (!mounted || loading) {
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
          <div className="flex flex-wrap gap-3.5 justify-center pt-2">
            <Link href="/register">
              <Button
                size="lg"
                className="px-8 text-base h-12 shadow-lg shadow-primary/20
                           hover:shadow-primary/30 hover:-translate-y-0.5
                           transition-all duration-200 font-medium"
              >
                Get Started for Free
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
              className="group relative p-5 rounded-xl border border-border/50
                         bg-card/40 backdrop-blur-sm
                         hover:bg-card/70 hover:border-primary/30
                         hover:-translate-y-0.5 transition-all duration-200
                         flex flex-col gap-2"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center
                              text-primary group-hover:bg-primary/20 transition-colors duration-200">
                <Icon className="w-4 h-4" />
              </div>
              <h3 className="font-semibold text-sm text-foreground tracking-tight">
                {title}
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Enhanced Footer ────────────────────────────────────────────────── */}
      <footer className="border-t border-border/40 bg-card/20 backdrop-blur-md mt-auto">
        <div className="max-w-6xl mx-auto px-6 py-12 md:py-16 grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12">
          
          {/* Brand Info */}
          <div className="md:col-span-5 space-y-4">
            <div className="flex items-center gap-2.5">
              <img src="/logo.jpg" alt="Logo" className="w-7 h-7 rounded-lg object-cover shadow-sm" />
              <span className="font-bold text-base tracking-tight text-foreground">
                Document AI Analyst
              </span>
            </div>
            <p className="text-xs text-muted-foreground max-w-sm leading-relaxed">
              Enterprise Agentic Retrieval-Augmented Generation (RAG) platform. Turn complex PDFs, contracts, and research papers into interactive, verified intelligence.
            </p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground/80 pt-1">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                All Systems Operational
              </span>
            </div>
          </div>

          {/* Column 1: Product */}
          <div className="md:col-span-2 space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground/80">Product</h4>
            <ul className="space-y-2.5 text-xs text-muted-foreground">
              <li>
                <Link href="/register" className="hover:text-foreground transition-colors">Get Started</Link>
              </li>
              <li>
                <Link href="/login" className="hover:text-foreground transition-colors">Sign In</Link>
              </li>
              <li>
                <Link href="/dashboard" className="hover:text-foreground transition-colors">Workspace</Link>
              </li>
            </ul>
          </div>

          {/* Column 2: Resources & Community */}
          <div className="md:col-span-3 space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground/80">Resources</h4>
            <ul className="space-y-2.5 text-xs text-muted-foreground">
              <li>
                <a href={docsUrl} target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors inline-flex items-center gap-1">
                  API Documentation ↗
                </a>
              </li>
              <li>
                <button 
                  onClick={() => setHallOfFameOpen(true)}
                  className="hover:text-foreground transition-colors text-left"
                >
                  Hall of Fame (Contributors)
                </button>
              </li>
              <li>
                <a href="https://github.com/param20h/PDF-Assistant-RAG" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors inline-flex items-center gap-1">
                  GitHub Repository ↗
                </a>
              </li>
            </ul>
          </div>

          {/* Column 3: Legal */}
          <div className="md:col-span-2 space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground/80">Legal & Trust</h4>
            <ul className="space-y-2.5 text-xs text-muted-foreground">
              <li>
                <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy Policy</Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-foreground transition-colors">Terms of Service</Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="max-w-6xl mx-auto px-6 py-6 border-t border-border/20 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-[11px] text-muted-foreground/70">
            &copy; {new Date().getFullYear()} Document AI Analyst. Open-source under Apache-2.0.
          </p>
          <p className="text-[11px] text-muted-foreground/60 flex flex-wrap items-center gap-1.5 justify-center">
            Powered by
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

      {/* Maintenance Pop-up Banner */}
      {maintenanceVisible && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm p-4 rounded-xl border border-amber-500/30 bg-background/95 backdrop-blur-md shadow-2xl shadow-amber-500/5 flex flex-col gap-2.5 animate-fade-in-up">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
              <h4 className="font-semibold text-sm text-foreground">System Maintenance</h4>
            </div>
            <button 
              onClick={() => setMaintenanceVisible(false)}
              className="text-muted-foreground hover:text-foreground text-xs p-1"
              aria-label="Dismiss maintenance alert"
            >
              ✕
            </button>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            We are currently running database updates. Some features may be temporarily offline, but the app will be fully live soon!
          </p>
        </div>
      )}
    </div>
  );
}
