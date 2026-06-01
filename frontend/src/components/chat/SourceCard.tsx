"use client";

import { useState } from "react";
import type { SourceBoundingBox, SourceChunk } from "@/store/chat-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ChevronDown, ChevronUp, FileText, Eye, TextQuote } from "lucide-react";

const EXCERPT_THRESHOLD = 200;

type ConfidenceLevel = "High" | "Medium" | "Low" | "Unknown";

interface ConfidenceBadgeMeta {
  label: ConfidenceLevel;
  className: string;
}

const normalizeMetricValue = (value?: number) => {
  if (typeof value !== "number" || Number.isNaN(value)) return undefined;
  return value > 1 ? value / 100 : value;
};

const formatMetricValue = (value?: number) => {
  const normalizedValue = normalizeMetricValue(value);
  if (normalizedValue === undefined) return "N/A";
  return `${Math.round(normalizedValue * 100)}%`;
};

const getConfidenceBadgeMeta = (value?: number): ConfidenceBadgeMeta => {
  const normalizedValue = normalizeMetricValue(value);

  if (normalizedValue === undefined) {
    return {
      label: "Unknown",
      className: "border-muted bg-muted/40 text-muted-foreground",
    };
  }

  if (normalizedValue >= 0.8) {
    return {
      label: "High",
      className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600",
    };
  }

  if (normalizedValue >= 0.5) {
    return {
      label: "Medium",
      className: "border-amber-500/30 bg-amber-500/10 text-amber-600",
    };
  }

  return {
    label: "Low",
    className: "border-red-500/30 bg-red-500/10 text-red-600",
  };
};

const getPrimarySourceMetric = (source: SourceChunk) =>
  source.confidence ?? source.score;

const MetricBadge = ({
  label,
  value,
}: {
  label: "Score" | "Confidence";
  value?: number;
}) => {
  const badgeMeta = getConfidenceBadgeMeta(value);

  return (
    <Badge
      variant="outline"
      className={`h-5 px-1.5 text-[9px] font-medium ${badgeMeta.className}`}
      title={`${label}: ${formatMetricValue(value)}`}
    >
      {label}: {badgeMeta.label}
    </Badge>
  );
};

interface Props {
  sources: SourceChunk[];
  onPageClick: (payload: {
    page: number;
    highlightRects?: SourceBoundingBox[];
  }) => void;
}

export default function SourceCard({ sources = [], onPageClick }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [excerptOpen, setExcerptOpen] = useState<Set<number>>(new Set());

  if (sources.length === 0) return null;

  const toggleExcerpt = (index: number) => {
    const next = new Set(excerptOpen);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    setExcerptOpen(next);
  };

  return (
    <div className="rounded-lg border border-border/50 bg-card/50 overflow-hidden">
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

      {!expanded && (
        <div className="px-3 pb-2 flex flex-wrap gap-1">
          {sources.map((src, i) => {
            const badgeMeta = getConfidenceBadgeMeta(
              getPrimarySourceMetric(src)
            );

            return (
              <Tooltip key={i}>
                <TooltipTrigger className="inline-flex">
                  <Badge
                    variant="outline"
                    className={`text-[10px] h-5 cursor-pointer hover:bg-primary/20 transition-colors ${badgeMeta.className}`}
                    onClick={() => onPageClick(src.page + 1)}
                  >
                    p.{src.page + 1} - {badgeMeta.label}
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={() =>
                    onPageClick({
                      page: source.page + 1,
                      highlightRects: source.highlightRects,
                    })
                  }
                >
                  <div className="mb-1 flex flex-wrap gap-1">
                    <MetricBadge label="Score" value={src.score} />
                    <MetricBadge label="Confidence" value={src.confidence} />
                  </div>
                  <p className="text-[11px] leading-relaxed line-clamp-6">
                    {src.text}
                  </p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      )}

      {expanded && (
        <div className="border-t border-border/30">
          {sources.map((src, i) => (
            <div
              key={i}
              className="px-3 py-2.5 border-b border-border/20 last:border-b-0 hover:bg-accent/20 transition-colors"
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <span className="truncate text-[10px] font-medium text-muted-foreground">
                    {src.filename}
                  </span>
                  <Badge variant="outline" className="h-5 px-1.5 text-[9px]">
                    Page {src.page + 1}
                  </Badge>
                  <MetricBadge label="Score" value={src.score} />
                  <MetricBadge label="Confidence" value={src.confidence} />
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 shrink-0 px-2 text-[10px]"
                  onClick={() => onPageClick(src.page + 1)}
                >
                  <Eye className="w-3 h-3 mr-1" />
                  View
                </Button>
              </div>
              <p
                className={`text-[11px] text-muted-foreground leading-relaxed ${
                  excerptOpen.has(i) ? "" : "line-clamp-3"
                }`}
              >
                {src.text}
              </p>
              {src.text.length > EXCERPT_THRESHOLD && (
                <button
                  onClick={() => toggleExcerpt(i)}
                  className="mt-1.5 flex items-center gap-1 text-[10px] text-primary/70 hover:text-primary transition-colors"
                >
                  <TextQuote className="w-3 h-3" />
                  {excerptOpen.has(i) ? "Hide excerpt" : "Show excerpt"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
