"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Menu } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import { api, CONNECTION_ERROR_BANNER_MESSAGE, CONNECTION_ERROR_MESSAGE } from "@/lib/api";
import Header from "@/components/layout/Header";
import DocumentSidebar from "@/components/document/DocumentSidebar";
import ChatSessionSidebar from "@/components/chat/ChatSessionSidebar";
import ChatPanel from "@/components/chat/ChatPanel";
function PDFViewerSkeleton() {
  return (
    <div
      className="h-full flex flex-col bg-background"
      aria-busy="true"
      aria-label="Loading PDF viewer"
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-card/50 shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-muted/70 animate-pulse" />
          <div className="h-7 w-20 rounded-md bg-muted/70 animate-pulse" />
          <div className="h-7 w-7 rounded-md bg-muted/70 animate-pulse" />
        </div>
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-muted/70 animate-pulse" />
          <div className="h-4 w-10 rounded bg-muted/70 animate-pulse" />
          <div className="h-7 w-7 rounded-md bg-muted/70 animate-pulse" />
        </div>
      </div>
      <div className="flex-1 p-4">
        <div className="h-full rounded-lg border border-border/50 bg-muted/40 animate-pulse" />
      </div>
    </div>
  );
}

const PDFViewer = dynamic(() => import("@/components/document/PDFViewer"), {
  ssr: false,
  loading: () => <PDFViewerSkeleton />,
});

export interface DocInfo {
  chunk_size?: number;
  chunk_overlap?: number;
  summary: string;
  id: string;
  original_name: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  status: string;
  error_message: string | null;
  uploaded_at: string;
}

export default function DashboardPage() {
  const { user, loading, initialized } = useAuth();
  const router = useRouter();

  const [documents, setDocuments] = useState<DocInfo[]>([]);
  const prevDocsRef = useRef<Record<string, string>>({});
  const [activeDoc, setActiveDoc] = useState<DocInfo | null>(null);
  const [pdfPage, setPdfPage] = useState(1);
  const [pdfHighlightTarget, setPdfHighlightTarget] = useState<{
    page: number;
    rects?: {
      left: number;
      top: number;
      width: number;
      height: number;
      unit?: "percent" | "pixels" | "pdf";
    }[];
  } | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(true);
  const [connectionError, setConnectionError] = useState("");
  const [documentsLoading, setDocumentsLoading] = useState(true);

  const handleDocumentRenamed = useCallback((renamedDocument: DocInfo) => {
    setDocuments((current) =>
      current.map((document) => (document.id === renamedDocument.id ? renamedDocument : document))
    );
    setActiveDoc((current) => (current?.id === renamedDocument.id ? renamedDocument : current));
  }, []);

  // Auth guard

  useEffect(() => {
    if (initialized && !user) router.replace("/login");
  }, [user, initialized, router]);

  // Check if Hugging Face token configuration is present
  useEffect(() => {
    if (user) {
      const hasHfToken = !!(user.hf_token || localStorage.getItem("hf_token"));

      if (!hasHfToken) {
        console.info(
          "Hugging Face API token is not configured. Personal model access will fall back to the system default unless set in the user profile menu."
        );
      }
    }
  }, [user]);


  // Load documents
  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    try {
      const data = await api.get<{ documents?: DocInfo[]; items?: DocInfo[] }>(
        "/api/v1/documents/"
      );
      setDocuments(data?.documents ?? data?.items ?? []);
      setConnectionError("");
    } catch (err) {
      const message = err instanceof Error ? err.message : CONNECTION_ERROR_MESSAGE;
      setConnectionError(
        message === CONNECTION_ERROR_MESSAGE
          ? CONNECTION_ERROR_BANNER_MESSAGE
          : `⚠️ ${message}`
      );
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    void (async () => {
      await loadDocuments();
    })();
  }, [user, loadDocuments]);

  // Ingest status change toast notification handler
  useEffect(() => {
    const prev = prevDocsRef.current;
    const nextPrevDocs: Record<string, string> = {};
    (documents || []).forEach((doc) => {
      nextPrevDocs[doc.id] = doc.status;

      const oldStatus = prev[doc.id];
      if (oldStatus && oldStatus !== doc.status) {
        if (doc.status === "ready") {
          toast.success(`🎉 Ingestion complete: '${doc.original_name}' is ready!`);
        } else if (doc.status === "failed") {
          toast.error(`❌ Ingestion failed for '${doc.original_name}': ${doc.error_message || "Unknown error"}`);
        }
      }
    });
    prevDocsRef.current = nextPrevDocs;
  }, [documents]);

  // Poll for processing status
  useEffect(() => {
    const hasPending = (documents || []).some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!hasPending) return;

    const interval = setInterval(loadDocuments, 3000);
    return () => clearInterval(interval);
  }, [documents, loadDocuments]);

  // Prevent background scroll on mobile while drawer is open
  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [sidebarOpen]);

  if (!initialized || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse-glow w-12 h-12 rounded-full bg-primary/20" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <div className="relative flex-shrink-0 z-50">
        <button
          onClick={() => setSidebarOpen(true)}
          className="
            md:hidden
            absolute left-3 top-1/2 -translate-y-1/2 z-[60]
            p-2 rounded-md
            text-gray-600 hover:text-gray-900
            dark:text-gray-400 dark:hover:text-gray-100
            hover:bg-gray-100 dark:hover:bg-gray-800
            transition-colors
          "
          aria-label="Open document sidebar"
          aria-expanded={sidebarOpen}
          aria-controls="document-sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        <Header
          sidebarOpen={panelOpen}
          onToggleSidebar={() => setPanelOpen(!panelOpen)}
          viewerOpen={viewerOpen}
          onToggleViewer={() => setViewerOpen(!viewerOpen)}
        />
      </div>

      {connectionError && (
        <div
          role="alert"
          className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive"
        >
          {connectionError}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* ── Left: Document Sidebar ─────────── */}
        <div
          className={`w-0 flex-shrink-0 overflow-visible md:overflow-hidden md:w-72 md:border-r md:border-border/50 md:animate-fade-in-up ${panelOpen ? "md:block" : "md:hidden"}`}
        >
          <DocumentSidebar
            documents={documents}
            activeDoc={activeDoc}
            loading={documentsLoading}
            onSelectDoc={(doc) => {
              setActiveDoc(doc);
              setPdfPage(1);
              setSidebarOpen(false);
            }}
            onDocumentsChange={loadDocuments}
            onDocumentRenamed={handleDocumentRenamed}
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />
        </div>

        {/* ── Left-Center: Chat Sessions Sidebar ──── */}
        <ChatSessionSidebar />

        {/* ── Center: Chat Panel ──────────────────────────────────── */}
        <div className="flex-1 min-w-0 flex flex-col">
          <ChatPanel
            activeDoc={activeDoc}
            onCitationClick={(target) => {
              setPdfPage(target.page);
              setPdfHighlightTarget({ page: target.page, rects: target.highlightRects });
              if (!viewerOpen) setViewerOpen(true);
            }}
          />
        </div>

        {/* ── Right: PDF Viewer — hidden on mobile ────────────────── */}
        {viewerOpen && activeDoc && activeDoc.original_name.endsWith(".pdf") && (
          <div className="hidden md:block w-[480px] flex-shrink-0 border-l border-border/50 overflow-hidden animate-fade-in-up">
            <PDFViewer
              documentId={activeDoc.id}
              currentPage={pdfPage}
              onPageChange={(page) => {
                setPdfPage(page);
                if (pdfHighlightTarget?.page !== page) {
                  setPdfHighlightTarget(null);
                }
              }}
              totalPages={activeDoc.page_count}
              highlightTarget={pdfHighlightTarget}
            />
          </div>
        )}
      </div>
    </div>
  );
}
