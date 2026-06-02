"use client";

import { useState } from "react";
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

interface Props {
  documentId: string;
  currentPage: number;
  onPageChange: (page: number) => void;
  totalPages: number;
}

export default function PDFViewer({ documentId, currentPage, onPageChange, totalPages }: Props) {
  const [scale, setScale] = useState(1.0);
  const [, setLoading] = useState(true);
  const [pageInput, setPageInput] = useState(String(currentPage));
  const [prevCurrentPage, setPrevCurrentPage] = useState(currentPage);

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

          <form
            onSubmit={handlePageSubmit}
            className="flex items-center gap-1 text-xs"
            aria-label="PDF page navigation"
          >
            <Input
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              className="w-10 h-7 text-center text-xs p-0 bg-background/50"
              aria-label={`PDF page number, current page ${currentPage} of ${totalPages}`}
              inputMode="numeric"
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
            onClick={() => setScale((s) => Math.max(0.5, s - 0.15))}
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
            onClick={() => setScale((s) => Math.min(2.5, s + 0.15))}
            aria-label="Zoom in PDF"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* ── PDF Render ──────────────────────────────── */}
      <div className="flex-1 overflow-auto bg-muted/30 flex justify-center items-start p-4 relative w-full">
        <Document
          file={fileConfig}
          onLoadSuccess={() => setLoading(false)}
          onLoadError={(err) => {
            console.error("PDF load error:", err);
            setLoading(false);
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
        </Document>
      </div>
    </div>
  );
}
