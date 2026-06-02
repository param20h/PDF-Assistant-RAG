"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2, AlertCircle } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { Document, Page, pdfjs } from "react-pdf";

// Import styles for react-pdf layers
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Configure PDF.js worker using standard unpkg URL
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export interface PdfHighlightRect {
  left: number;
  top: number;
  width: number;
  height: number;
  unit?: "percent" | "pixels" | "pdf";
}

export interface PdfHighlightTarget {
  page: number;
  rects?: PdfHighlightRect[];
}

interface Props {
  documentId: string;
  currentPage: number;
  onPageChange: (page: number) => void;
  totalPages: number;
  highlightTarget?: PdfHighlightTarget | null;
}

const isNormalizedRect = (rect: PdfHighlightRect) =>
  rect.left >= 0 &&
  rect.left <= 1 &&
  rect.top >= 0 &&
  rect.top <= 1 &&
  rect.width >= 0 &&
  rect.width <= 1 &&
  rect.height >= 0 &&
  rect.height <= 1;

export default function PDFViewer({
  documentId,
  currentPage,
  onPageChange,
  totalPages,
  highlightTarget,
}: Props) {
  const [scale, setScale] = useState(1.0);
  const [pageInput, setPageInput] = useState(String(currentPage));
  const [prevCurrentPage, setPrevCurrentPage] = useState(currentPage);
  const viewerRef = useRef<HTMLDivElement>(null);

  // Sync page input state with current page prop updates during render phase
  if (currentPage !== prevCurrentPage) {
    setPrevCurrentPage(currentPage);
    setPageInput(String(currentPage));
  }

  const pdfUrl = `${API_BASE}/api/v1/documents/${documentId}/pdf`;
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  // Configure file object with Authorization headers
  const fileConfig = {
    url: pdfUrl,
    httpHeaders: token ? { Authorization: `Bearer ${token}` } : undefined,
  };



  useEffect(() => {
    if (viewerRef.current && highlightTarget?.page === currentPage) {
      viewerRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [currentPage, highlightTarget?.page]);

  const overlayRects = useMemo(() => {
    if (!highlightTarget || highlightTarget.page !== currentPage) return [];

    return (highlightTarget.rects ?? []).map((rect) => {
      if (rect.unit === "percent" || isNormalizedRect(rect)) {
        return {
          left: `${rect.left * 100}%`,
          top: `${rect.top * 100}%`,
          width: `${rect.width * 100}%`,
          height: `${rect.height * 100}%`,
        };
      }

      if (rect.unit === "pixels" || rect.unit == null) {
        return {
          left: `${rect.left}px`,
          top: `${rect.top}px`,
          width: `${rect.width}px`,
          height: `${rect.height}px`,
        };
      }

      return {
        left: `${rect.left}px`,
        top: `${rect.top}px`,
        width: `${rect.width}px`,
        height: `${rect.height}px`,
      };
    });
  }, [highlightTarget, currentPage]);



  return (
    <div className="h-full flex flex-col bg-background" ref={viewerRef}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-card/50 shrink-0">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => {
              const newPage = Math.max(1, currentPage - 1);
              onPageChange(newPage);
              setPageInput(String(newPage));
            }}
            disabled={currentPage <= 1}
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              const pageNumber = parseInt(pageInput.trim(), 10);
              if (!Number.isNaN(pageNumber) && pageNumber >= 1 && pageNumber <= totalPages) {
                onPageChange(pageNumber);
              } else {
                setPageInput(String(currentPage));
              }
            }}
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
            onClick={() => {
              const newPage = Math.min(totalPages, currentPage + 1);
              onPageChange(newPage);
              setPageInput(String(newPage));
            }}
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
            onClick={() => setScale((current) => Math.max(0.5, current - 0.15))}
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
            onClick={() => setScale((current) => Math.min(2.5, current + 0.15))}
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* ── PDF Render ──────────────────────────────── */}
      <div className="flex-1 overflow-auto bg-muted/30 flex justify-center items-start p-4 relative w-full">
        <Document
          file={fileConfig}
          onLoadError={(err) => {
            console.error("PDF load error:", err);
          }}
          loading={
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          }
          error={
            <div className="flex flex-col items-center justify-center p-8 text-center bg-card border border-destructive/20 rounded-lg max-w-md mx-auto my-12 shadow-sm gap-3">
              <AlertCircle className="w-8 h-8 text-destructive animate-pulse" />
              <div>
                <p className="font-semibold text-sm text-foreground mb-1">Failed to load PDF</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  We encountered an error loading this PDF document. Please verify the document is ready or try refreshing the page.
                </p>
              </div>
            </div>
          }
          noData={
            <div className="flex flex-col items-center justify-center p-8 text-center bg-card border border-border rounded-lg max-w-md mx-auto my-12 shadow-sm gap-2">
              <p className="font-semibold text-sm text-foreground">No PDF document selected</p>
              <p className="text-xs text-muted-foreground">Select or upload a document to view it here.</p>
            </div>
          }
          className="shadow-md border border-border bg-card max-w-full"
        >
          <div className="relative">
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderAnnotationLayer={false}
              renderTextLayer={true}
              loading={
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              }
            />
            <div className="absolute inset-0 pointer-events-none z-10">
              {overlayRects.map((style, index) => (
                <div
                  key={index}
                  className="absolute bg-yellow-400/40 rounded-sm border border-yellow-300/50"
                  style={style}
                />
              ))}
            </div>
          </div>
        </Document>
      </div>
    </div>
  );
}
