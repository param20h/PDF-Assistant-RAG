"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import Header from "@/components/layout/Header";
import DocumentSidebar from "@/components/document/DocumentSidebar";
import ChatPanel from "@/components/chat/ChatPanel";
import PDFViewer from "@/components/document/PDFViewer";

export interface DocInfo {
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
  const { user, loading } = useAuth();
  const router = useRouter();

  const [documents, setDocuments] = useState<DocInfo[]>([]);
  const [activeDoc, setActiveDoc] = useState<DocInfo | null>(null);
  const [pdfPage, setPdfPage] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [viewerOpen, setViewerOpen] = useState(true);

  // Auth guard
  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  // Load documents
  const loadDocuments = useCallback(async () => {
    try {
      const data = await api.get<{ documents: DocInfo[] }>("/api/v1/documents/");
      setDocuments(data.documents);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    if (user) loadDocuments();
  }, [user, loadDocuments]);

  // Poll for processing status
  useEffect(() => {
    const hasPending = documents.some(
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

      <div className="flex-1 flex overflow-hidden">
        {/* ── Left: Document Sidebar ──────────────── */}
        {sidebarOpen && (
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
        )}

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
        {viewerOpen && activeDoc && activeDoc.original_name.endsWith(".pdf") && (
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
