"use client";

import { useState } from "react";
import type { SourceChunk } from "./ChatPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, FileText, Eye } from "lucide-react";

interface Props {
  sources: SourceChunk[];
  onPageClick: (page: number) => void;
}

export default function SourceCard({ sources, onPageClick }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="rounded-lg border border-border/50 bg-card/50 overflow-hidden">
      {/* ── Header ──────────────────────────────────── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-accent/30 transition-colors"
      >
        <span className="flex items-center gap-1.5 text-muted-foreground">
          <FileText className="w-3.5 h-3.5" />
          {sources.length} source{sources.length > 1 ? "s" : ""} cited
        </span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
        )}
      </button>

      {/* ── Collapsed: Mini badges ──────────────────── */}
      {!expanded && (
        <div className="px-3 pb-2 flex flex-wrap gap-1">
          {sources.map((src, i) => (
            <Badge
              key={i}
              variant="secondary"
              className="text-[10px] h-5 cursor-pointer hover:bg-primary/20 transition-colors"
              onClick={() => onPageClick(src.page)}
            >
              p.{src.page} • {src.confidence}%
            </Badge>
          ))}
        </div>
      )}

      {/* ── Expanded: Full source cards ─────────────── */}
      {expanded && (
        <div className="border-t border-border/30">
          {sources.map((src, i) => (
            <div
              key={i}
              className="px-3 py-2.5 border-b border-border/20 last:border-b-0 hover:bg-accent/20 transition-colors"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-medium text-muted-foreground">
                    {src.filename}
                  </span>
                  <Badge variant="outline" className="text-[9px] h-4 px-1.5">
                    Page {src.page}
                  </Badge>
                  <Badge
                    variant="secondary"
                    className={`text-[9px] h-4 px-1.5 ${
                      src.confidence >= 80
                        ? "text-emerald-400 bg-emerald-400/10"
                        : src.confidence >= 50
                        ? "text-yellow-400 bg-yellow-400/10"
                        : "text-muted-foreground"
                    }`}
                  >
                    {src.confidence}% match
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={() => onPageClick(src.page)}
                >
                  <Eye className="w-3 h-3 mr-1" />
                  View
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-3">
                {src.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
