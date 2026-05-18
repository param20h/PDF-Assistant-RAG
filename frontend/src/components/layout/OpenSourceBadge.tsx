"use client";

import { useState, useEffect } from "react";
import { Github, Star, GitFork, Heart, Trophy } from "lucide-react";

interface Props {
  onOpenHallOfFame: () => void;
}

export default function OpenSourceBadge({ onOpenHallOfFame }: Props) {
  const [stars, setStars] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    fetch("https://api.github.com/repos/param20h/PDF-Assistant-RAG")
      .then((r) => r.json())
      .then((d) => setStars(d.stargazers_count ?? null))
      .catch(() => {});

    // Pulse animation once on mount to draw attention
    const t = setTimeout(() => setHasAnimated(true), 2000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="fixed bottom-5 right-5 z-40 flex flex-col items-end gap-2">

      {/* Expanded card */}
      {expanded && (
        <div className="mb-1 w-64 rounded-2xl border border-border/60 bg-card/95 backdrop-blur-md shadow-2xl overflow-hidden animate-fade-in-up">
          {/* Top section */}
          <div className="px-4 pt-4 pb-3 border-b border-border/40">
            <div className="flex items-center gap-2 mb-1">
              <Github className="w-4 h-4" />
              <span className="text-sm font-semibold">Open Source</span>
              <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-400 font-medium border border-green-500/20">
                GSSOC
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Built in public with ❤️ by the community. Free forever.
            </p>
          </div>

          {/* Actions */}
          <div className="p-3 flex flex-col gap-2">
            <a
              href="https://github.com/param20h/PDF-Assistant-RAG"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between px-3 py-2 rounded-lg bg-muted/50 hover:bg-accent transition-colors group"
            >
              <div className="flex items-center gap-2 text-xs">
                <Star className="w-3.5 h-3.5 text-yellow-500" />
                <span>Star on GitHub</span>
              </div>
              {stars !== null && (
                <span className="text-xs font-bold text-yellow-500">{stars} ⭐</span>
              )}
            </a>

            <a
              href="https://github.com/param20h/PDF-Assistant-RAG/fork"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 hover:bg-accent transition-colors text-xs"
            >
              <GitFork className="w-3.5 h-3.5 text-primary" />
              <span>Fork & Contribute</span>
            </a>

            <button
              onClick={() => { setExpanded(false); onOpenHallOfFame(); }}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10 hover:bg-primary/20 transition-colors text-xs text-primary border border-primary/20 cursor-pointer w-full"
            >
              <Trophy className="w-3.5 h-3.5" />
              <span>Hall of Fame 🏆</span>
            </button>
          </div>

          {/* Heart footer */}
          <div className="px-4 pb-3 flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <Heart className="w-3 h-3 text-red-400 fill-red-400" />
            <span>Made with contributors worldwide</span>
          </div>
        </div>
      )}

      {/* FAB trigger button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`
          group flex items-center gap-2 px-3 py-2 rounded-full
          border border-border/60 bg-card/90 backdrop-blur-md shadow-lg
          hover:border-primary/50 hover:shadow-primary/10 hover:shadow-xl
          transition-all duration-300 cursor-pointer
          ${!hasAnimated ? "animate-pulse-glow" : ""}
        `}
        title="Open Source — Support this project"
      >
        <Github className="w-4 h-4 group-hover:text-primary transition-colors" />
        <span className="text-xs font-medium hidden sm:inline">Open Source</span>
        {stars !== null && (
          <span className="flex items-center gap-0.5 text-[11px] font-semibold text-yellow-500">
            <Star className="w-3 h-3 fill-yellow-500" />
            {stars >= 1000 ? `${(stars / 1000).toFixed(1)}k` : stars}
          </span>
        )}
      </button>
    </div>
  );
}
