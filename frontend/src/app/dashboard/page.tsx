"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  api,
  CONNECTION_ERROR_BANNER_MESSAGE,
  CONNECTION_ERROR_MESSAGE,
} from "@/lib/api";

import Header from "@/components/layout/Header";
import DocumentSidebar from "@/components/document/DocumentSidebar";
import ChatPanel from "@/components/chat/ChatPanel";
import PDFViewer from "@/components/document/PDFViewer";
import { Skeleton } from "@/components/ui/skeleton";

export interface DocInfo {
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

function DocumentSkeleton() {
  return (
    <div className="w-72 flex-shrink-0 border-r border-border/50 p-4 space-y-4">
      {[1, 2, 3, 4].map((item) => (
        <div
          key={item}
          className="rounded-lg border border-border/50 p-4 space-y-3"
        >
          <Skeleton className="h-4 w-[180px]" />
          <Skeleton className="h-3 w-[120px]" />
          <Skeleton className="h-3 w-[90px]" />
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [documents, setDocuments] = useState<DocInfo[]>([]);
  const [activeDoc, setActiveDoc] = useState<DocInfo | null>(null);
  const [pdfPage, setPdfPage] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [viewerOpen, setViewerOpen] = useState(true);
  const [connectionError, setConnectionError] = useState("");
  const [documentsLoading, setDocumentsLoading] = useState(true);

  // Auth guard
  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  // Load documents
  const loadDocuments = useCallback(async () => {
    try {
      setDocumentsLoading(true);

      const data = await api.get<{ documents?: DocInfo[]; items?: DocInfo[] }>(
        "/api/v1/documents/"
      );

      setDocuments(data?.documents ?? data?.items ?? []);
      setConnectionError("");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : CONNECTION_ERROR_MESSAGE;

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

  // Poll for processing status
  useEffect(() => {
    const hasPending = (documents || []).some(
      (d) => d.status === "pending" || d.status === "processing"
    );

    if (!hasPending) return;

    const interval = setInterval(loadDocuments, 3000);

    return () => clearInterval(interval);
  }, [documents, loadDocuments]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse-glow w-12 h-12 rounded-full bg-primary/20" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        viewerOpen={viewerOpen}
        onToggleViewer={() => setViewerOpen(!viewerOpen)}
      />

      {connectionError && (
        <div
          role="alert"
          className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive"
        >
          {connectionError}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* ── Left: Document Sidebar / Skeleton ──────────────── */}
        {sidebarOpen &&
          (documentsLoading ? (
            <DocumentSkeleton />
          ) : (
            <div className="w-72 flex-shrink-0 border-r border-border/50 overflow-hidden animate-fade-in-up">
              <DocumentSidebar
                documents={documents}
                activeDoc={activeDoc}
                onSelectDoc={(doc) => {
                  setActiveDoc(doc);
                  setPdfPage(1);
                }}
                onDocumentsChange={loadDocuments}
              />
            </div>
          ))}

        {/* ── Center: Chat Panel ─────────────────── */}
        <div className="flex-1 min-w-0 flex flex-col">
          <ChatPanel
            activeDoc={activeDoc}
            onCitationClick={(page) => {
              setPdfPage(page);

              if (!viewerOpen) setViewerOpen(true);
            }}
          />
        </div>

        {/* ── Right: PDF Viewer ──────────────────── */}
        {viewerOpen &&
          activeDoc &&
          activeDoc.original_name.endsWith(".pdf") && (
            <div className="w-[480px] flex-shrink-0 border-l border-border/50 overflow-hidden animate-fade-in-up">
              <PDFViewer
                documentId={activeDoc.id}
                currentPage={pdfPage}
                onPageChange={setPdfPage}
                totalPages={activeDoc.page_count}
              />
            </div>
          )}
      </div>
    </div>
  );
}
