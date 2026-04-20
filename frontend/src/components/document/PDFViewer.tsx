"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2 } from "lucide-react";
import { API_BASE } from "@/lib/api";

interface Props {
  documentId: string;
  currentPage: number;
  onPageChange: (page: number) => void;
  totalPages: number;
}

export default function PDFViewer({ documentId, currentPage, onPageChange, totalPages }: Props) {
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [pageInput, setPageInput] = useState(String(currentPage));

  useEffect(() => {
    setPageInput(String(currentPage));
  }, [currentPage]);

  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const pdfUrl = `${API_BASE}/api/v1/documents/${documentId}/pdf`;

  // Use an iframe to render the PDF with the browser's native viewer
  // We append a page fragment for navigation
  const iframeSrc = `${pdfUrl}#page=${currentPage}`;

  const handlePageSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const num = parseInt(pageInput.trim());
    if (!isNaN(num) && num >= 1 && num <= totalPages) {
      onPageChange(num);
    } else {
      setPageInput(String(currentPage));
    }
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* ── Toolbar ─────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-card/50 shrink-0">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          <form
            onSubmit={handlePageSubmit}
            className="flex items-center gap-1 text-xs"
          >
            <Input
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              className="w-10 h-7 text-center text-xs p-0 bg-background/50"
            />
            <span className="text-muted-foreground">/ {totalPages}</span>
          </form>

          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setScale((s) => Math.max(0.5, s - 0.15))}
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </Button>
          <span className="text-[10px] text-muted-foreground min-w-[36px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setScale((s) => Math.min(2.5, s + 0.15))}
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* ── PDF Render ──────────────────────────────── */}
      <div className="flex-1 overflow-auto relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        )}
        <iframe
          key={`${documentId}-${currentPage}`}
          src={iframeSrc}
          className="w-full h-full border-0"
          style={{ transform: `scale(${scale})`, transformOrigin: "top left", width: `${100/scale}%`, height: `${100/scale}%` }}
          onLoad={() => setLoading(false)}
          title="PDF Viewer"
        />
      </div>
    </div>
  );
}
