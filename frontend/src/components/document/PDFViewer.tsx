"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2, AlertCircle, RotateCw } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { usePdfSearch } from "@/hooks/usePdfSearch";
import { PDFDocumentProxy } from "pdfjs-dist/types/src/display/api";

// Import styles for react-pdf layers
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Configure PDF.js worker locally using Next.js/Webpack asset bundling
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

interface SearchRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

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
  const [rotation, setRotation] = useState(0);
  const [pageInput, setPageInput] = useState(String(currentPage));
  const [pageInputError, setPageInputError] = useState(false);
  const [prevCurrentPage, setPrevCurrentPage] = useState(currentPage);
  const viewerRef = useRef<HTMLDivElement>(null);

  // --- NEW: Search State ---
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const { searchTerm, setSearchTerm, matches, currentIndex, setCurrentIndex, performSearch } = usePdfSearch();

  // Sync page input state with current page prop updates during render phase
  if (currentPage !== prevCurrentPage) {
    setPrevCurrentPage(currentPage);
    setPageInput(String(currentPage));
    setPageInputError(false);
  }

  const pdfUrl = `${API_BASE}/api/v1/documents/${documentId}/pdf`;
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  // Configure file object with Authorization headers (memoized to prevent re-renders)
  const fileConfig = useMemo(() => ({
    url: pdfUrl,
    httpHeaders: token ? { Authorization: `Bearer ${token}` } : undefined,
  }), [pdfUrl, token]);

  useEffect(() => {
    if (viewerRef.current && highlightTarget?.page === currentPage) {
      viewerRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [currentPage, highlightTarget?.page]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isModifier = e.ctrlKey || e.metaKey;
      if (isModifier) {
        if (e.key === "=" || e.key === "+") {
          e.preventDefault();
          setScale((s) => Math.min(2.0, s + 0.1));
        } else if (e.key === "-") {
          e.preventDefault();
          setScale((s) => Math.max(0.5, s - 0.1));
        } else if (e.key === "r" || e.key === "R") {
          e.preventDefault();
          setRotation((r) => (r + 90) % 360);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

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

  // --- NEW: Search Highlights Logic ---
  const searchHighlights = useMemo(() => {
    if (!matches[currentIndex] || matches[currentIndex].page !== currentPage) return [];
    return matches[currentIndex].rects.map((r: SearchRect) => ({
      left: `${r.left}px`,
      top: `${r.top}px`,
      width: `${r.width}px`,
      height: `${r.height}px`
    }));
  }, [matches, currentIndex, currentPage]);

  const handlePageJump = (value: string) => {
    const pageNumber = parseInt(value.trim(), 10);
    if (!Number.isNaN(pageNumber) && pageNumber >= 1 && pageNumber <= totalPages) {
      setPageInputError(false);
      onPageChange(pageNumber);
    } else {
      setPageInputError(true);
      setTimeout(() => {
        setPageInput(String(currentPage));
        setPageInputError(false);
      }, 1000);
    }
  };

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
            aria-label="Go to previous PDF page"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>

          {/* --- NEW: Search Integration --- */}
          <div className="flex items-center gap-2 border-l pl-2">
            <Input
              placeholder="Search..."
              className="h-7 w-32 text-xs"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                performSearch(pdfDoc, e.target.value);
              }}
            />
            {matches.length > 0 && (
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-muted-foreground">
                  {currentIndex + 1}/{matches.length}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => {
                    const prevIdx = Math.max(0, currentIndex - 1);
                    setCurrentIndex(prevIdx);
                    onPageChange(matches[prevIdx].page);
                  }}
                >
                  <ChevronLeft className="w-3 h-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => {
                    const nextIdx = Math.min(matches.length - 1, currentIndex + 1);
                    setCurrentIndex(nextIdx);
                    onPageChange(matches[nextIdx].page);
                  }}
                >
                  <ChevronRight className="w-3 h-3" />
                </Button>
              </div>
            )}
          </div>

          {/* Page jump input — Page X of Y */}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              handlePageJump(pageInput);
            }}
            className="flex items-center gap-1 text-xs"
            aria-label="PDF page navigation"
          >
            <span className="text-muted-foreground text-[10px] hidden sm:inline">Page</span>
            <Input
              value={pageInput}
              onChange={(e) => {
                setPageInput(e.target.value);
                setPageInputError(false);
              }}
              onBlur={() => handlePageJump(pageInput)}
              className={`h-7 text-center text-xs p-0 bg-background/50 transition-colors ${
                String(currentPage).length >= 3 ? "w-14" : "w-10"
              } ${pageInputError ? "border-destructive text-destructive" : ""}`}
              aria-label={`Page number input, current page ${currentPage} of ${totalPages}`}
              aria-invalid={pageInputError}
              title={`Enter page number between 1 and ${totalPages}`}
              inputMode="numeric"
            />
            <span className="text-muted-foreground text-[10px]">of {totalPages}</span>
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
            aria-label="Go to next PDF page"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setScale((current) => Math.max(0.5, current - 0.1))}
            aria-label="Zoom out PDF"
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
            onClick={() => setScale((current) => Math.min(2.0, current + 0.1))}
            aria-label="Zoom in PDF"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setRotation((current) => (current + 90) % 360)}
            aria-label="Rotate PDF"
            title="Rotate 90°"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            className="h-7 px-2 text-[10px] font-medium"
            onClick={() => {
              setScale(1.0);
              setRotation(0);
            }}
            aria-label="Reset PDF zoom and rotation"
            title="Reset to 100% and 0°"
          >
            Reset
          </Button>
        </div>
      </div>

      {/* ── PDF Render ──────────────────────────────── */}
      <div className="flex-1 overflow-auto bg-muted/30 flex justify-center items-start p-4 relative w-full">
        <Document
          file={fileConfig}
          onLoadSuccess={(pdf) => setPdfDoc(pdf)} // NEW: Capture PDF Doc instance
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
                <p className="font-semibold text-sm text-foreground mb-1">
                  Failed to load PDF
                </p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  We encountered an error loading this PDF document. Please
                  verify the document is ready or try refreshing the page.
                </p>
              </div>
            </div>
          }
          noData={
            <div className="flex flex-col items-center justify-center p-8 text-center bg-card border border-border rounded-lg max-w-md mx-auto my-12 shadow-sm gap-2">
              <p className="font-semibold text-sm text-foreground">
                No PDF document selected
              </p>
              <p className="text-xs text-muted-foreground">
                Select or upload a document to view it here.
              </p>
            </div>
          }
          className="shadow-md border border-border bg-card max-w-full"
        >
          <div className="relative">
            <Page
              pageNumber={currentPage}
              scale={scale}
              rotate={rotation}
              renderAnnotationLayer={false}
              renderTextLayer={true}
              loading={
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              }
            />
            {/* Overlay Container (RAG + Search) */}
            <div className="absolute inset-0 pointer-events-none z-10">
              {overlayRects.map((style, index) => (
                <div
                  key={`rag-${index}`}
                  className="absolute bg-yellow-400/40 rounded-sm border border-yellow-300/50"
                  style={style}
                />
              ))}
              {searchHighlights.map((style, index) => (
                <div
                  key={`search-${index}`}
                  className="absolute bg-blue-400/40 rounded-sm border border-blue-300/50"
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