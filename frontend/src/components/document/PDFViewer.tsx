"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs, type PDFPageProxy } from "react-pdf";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2 } from "lucide-react";
import { API_BASE } from "@/lib/api";

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
  const [loadedPageKey, setLoadedPageKey] = useState(`${documentId}-${currentPage}`);
  const [pageDimensions, setPageDimensions] = useState({ width: 0, height: 0 });
  const viewerRef = useRef<HTMLDivElement | null>(null);

  const pdfUrl = `${API_BASE}/api/v1/documents/${documentId}/pdf`;
  const pageKey = `${documentId}-${currentPage}`;
  const loading = loadedPageKey !== pageKey;

  useEffect(() => {
    if (highlightTarget?.page && highlightTarget.page !== currentPage) {
      onPageChange(highlightTarget.page);
    }
  }, [highlightTarget?.page, currentPage, onPageChange]);

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

  const handleDocumentLoadSuccess = () => {
    setLoadedPageKey(pageKey);
  };

  const handlePageLoadSuccess = (page: PDFPageProxy) => {
    const viewport = page.getViewport({ scale });
    setPageDimensions({ width: viewport.width, height: viewport.height });
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-background" ref={viewerRef}>
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
            onSubmit={(e) => {
              e.preventDefault();
              const input = e.currentTarget.querySelector('input');
              const value = input?.value ?? "";
              const num = parseInt(String(value).trim());
              if (!isNaN(num) && num >= 1 && num <= totalPages) {
                onPageChange(num);
              }
            }}
            className="flex items-center gap-1 text-xs"
          >
            <Input
              key={currentPage}
              defaultValue={String(currentPage)}
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

      <div className="flex-1 overflow-auto relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        )}

        <div className="flex justify-center p-4">
          <div className="relative" style={{ width: pageDimensions.width || "100%" }}>
            <Document file={pdfUrl} onLoadSuccess={handleDocumentLoadSuccess}>
              <Page
                pageNumber={currentPage}
                scale={scale}
                onLoadSuccess={handlePageLoadSuccess}
                renderAnnotationLayer={false}
                renderTextLayer={false}
              />
            </Document>
            <div className="absolute inset-0 pointer-events-none">
              {overlayRects.map((style, index) => (
                <div
                  key={index}
                  className="absolute bg-yellow-400/40 rounded-sm border border-yellow-300/50"
                  style={style}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
