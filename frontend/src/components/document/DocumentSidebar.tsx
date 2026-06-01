"use client";

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import type { DocInfo } from "@/app/dashboard/page";
import { api } from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  FileText, Upload, Trash2, FileCheck, Clock, AlertCircle, Loader2, FolderOpen,
} from "lucide-react";
import { useDropzone } from "react-dropzone";
import { Settings } from "lucide-react";
import DocumentSettings from "./DocumentSettings";
import { toast } from "sonner";

interface Props {
  documents: DocInfo[];
  activeDoc: DocInfo | null;
  loading?: boolean;
  onSelectDoc: (doc: DocInfo) => void;
  onDocumentsChange: () => void;
  onDocumentRenamed: (doc: DocInfo) => void;
}

function DocumentListSkeleton() {
  return (
    <div className="space-y-2 pb-3" aria-hidden="true">
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="rounded-lg border border-sidebar-border/60 p-2.5">
          <div className="flex items-start gap-2.5">
            <Skeleton className="mt-0.5 h-4 w-4 rounded-full bg-sidebar-accent" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-4 w-4/5 bg-sidebar-accent" />
              <Skeleton className="h-3 w-full bg-sidebar-accent/80" />
              <div className="flex gap-2">
                <Skeleton className="h-3 w-10 bg-sidebar-accent/70" />
                <Skeleton className="h-3 w-12 bg-sidebar-accent/70" />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DocumentSidebar({
  documents = [],
  activeDoc,
  loading = false,
  onSelectDoc,
  onDocumentsChange,
  onDocumentRenamed,
}: Props) {
  const { t } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [settingsDoc, setSettingsDoc] = useState<DocInfo | null>(null);
  const [editingDocId, setEditingDocId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [renamingDocId, setRenamingDocId] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      void (async () => {
        setUploadError("");
        setUploading(true);
        setUploadProgress(0);

        try {
          for (let i = 0; i < acceptedFiles.length; i++) {
            const file = acceptedFiles[i];
            const formData = new FormData();
            formData.append("file", file);
            
            toast.info(`⏳ Uploading '${file.name}'...`);
            await api.postForm("/api/v1/documents/upload", formData);
            setUploadProgress(((i + 1) / acceptedFiles.length) * 100);
            toast.success(`📤 '${file.name}' uploaded successfully! Ingestion started.`);
          }
          onDocumentsChange();
        } catch (err) {
          const message = err instanceof Error ? err.message : t("documents.uploadFailed");
          setUploadError(message);
          toast.error(`❌ Upload failed: ${message}`);
        } finally {
          setUploading(false);
          setUploadProgress(0);
        }
      })();
    },
    [onDocumentsChange, t]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
    },
    disabled: uploading,
  });

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(t("documents.deleteConfirm"))) return;
    setDeleting(docId);
    try {
      await api.delete(`/api/v1/documents/${docId}`);
      onDocumentsChange();
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setDeleting(null);
    }
  };

  const handleSettingsClick = (doc: DocInfo, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering document selection
    setSettingsDoc(doc); 
  };

  const startRename = (doc: DocInfo, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEditingDocId(doc.id);
    setDraftName(doc.original_name);
  };

  const cancelRename = () => {
    setEditingDocId(null);
    setDraftName("");
  };

  const submitRename = async (doc: DocInfo) => {
    const nextName = draftName.trim();

    if (!nextName) {
      toast.error("Document name cannot be empty");
      return;
    }

    if (nextName === doc.original_name) {
      cancelRename();
      return;
    }

    const optimisticDoc = { ...doc, original_name: nextName };
    onDocumentRenamed(optimisticDoc);
    setRenamingDocId(doc.id);

    try {
      const updatedDoc = await api.renameDocument<DocInfo>(doc.id, nextName);
      onDocumentRenamed(updatedDoc);
      cancelRename();
      toast.success("Document renamed");
    } catch (err) {
      onDocumentRenamed(doc);
      const message = err instanceof Error ? err.message : "Rename failed";
      toast.error(message);
    } finally {
      setRenamingDocId(null);
    }
  };

  const handleRenameKeyDown = (doc: DocInfo, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      void submitRename(doc);
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelRename();
    }
  };

  const handleRowKeyDown = (doc: DocInfo, e: React.KeyboardEvent<HTMLDivElement>) => {
    if (editingDocId === doc.id || doc.status !== "ready") return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelectDoc(doc);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "ready":
        return <FileCheck className="w-3.5 h-3.5 text-emerald-400" />;
      case "processing":
        return <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />;
      case "pending":
        return <Clock className="w-3.5 h-3.5 text-yellow-400" />;
      case "failed":
        return <AlertCircle className="w-3.5 h-3.5 text-destructive" />;
      default:
        return <FileText className="w-3.5 h-3.5" />;
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <div className="h-full flex flex-col bg-sidebar">
      {/* ── Upload Zone ─────────────────────────────── */}
      <div className="p-3 border-b border-sidebar-border space-y-2">
        {uploadError && (
          <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive">
            {uploadError}
          </div>
        )}
        <div
          {...getRootProps()}
          className={`relative rounded-lg border-2 border-dashed p-4 text-center cursor-pointer transition-all duration-200
            ${isDragActive ? "border-primary bg-primary/10 scale-[1.02]" : "border-sidebar-border hover:border-primary/40 hover:bg-sidebar-accent/50"}
            ${uploading ? "pointer-events-none opacity-60" : ""}`}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <div className="space-y-2">
              <Loader2 className="w-5 h-5 mx-auto animate-spin text-primary" />
              <p className="text-xs text-muted-foreground">{t("documents.uploading")}</p>
              <Progress value={uploadProgress} className="h-1" />
            </div>
          ) : (
            <>
              <Upload className="w-5 h-5 mx-auto text-muted-foreground mb-2" />
              <p className="text-xs text-muted-foreground">
                {isDragActive ? t("documents.dropHere") : t("documents.dropOrClick")}
              </p>
              <p className="text-[10px] text-muted-foreground/60 mt-1">
                {t("documents.uploadFormats")}
              </p>
            </>
          )}
        </div>
      </div>

      {/* ── Documents List ──────────────────────────── */}
      <div className="px-3 pt-3 pb-1">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          {loading
            ? t("documents.documentsTitle", { count: "..." })
            : t("documents.documentsTitle", { count: documents.length })}
        </h3>
      </div>

      <ScrollArea className="flex-1 px-3 overflow-auto" aria-busy={loading}>
        {loading ? (
          <DocumentListSkeleton />
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <FolderOpen className="w-8 h-8 mx-auto text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">{t("documents.noDocuments")}</p>
            <p className="text-xs text-muted-foreground/60 mt-1">{t("documents.getStarted")}</p>
          </div>
        ) : (
          <div className="space-y-1 pb-3">
            {documents.map((doc) => {
              const isEditing = editingDocId === doc.id;
              const isRenaming = renamingDocId === doc.id;

              return (
                <div
                  key={doc.id}
                  role="button"
                  tabIndex={doc.status === "ready" ? 0 : -1}
                  onClick={() => doc.status === "ready" && !isEditing && onSelectDoc(doc)}
                  onKeyDown={(e) => handleRowKeyDown(doc, e)}
                  className={`w-full text-left p-2.5 rounded-lg transition-all duration-200 group
                    ${activeDoc?.id === doc.id
                      ? "bg-primary/15 border border-primary/30"
                      : "hover:bg-sidebar-accent border border-transparent"}
                    ${doc.status !== "ready" ? "opacity-60 cursor-default" : "cursor-pointer"}`}
                >
                  <div className="flex items-start gap-2.5">
                    {statusIcon(doc.status)}
                    <div className="flex-1 min-w-0">
                      {isEditing ? (
                        <Input
                          value={draftName}
                          onChange={(e) => setDraftName(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          onKeyDown={(e) => handleRenameKeyDown(doc, e)}
                          disabled={isRenaming}
                          autoFocus
                          className="h-7 px-2 text-sm font-medium"
                        />
                      ) : (
                        <p
                          className="text-sm font-medium truncate leading-tight"
                          onDoubleClick={(e) => startRename(doc, e)}
                          title="Double-click to rename"
                        >
                          {doc.original_name}
                        </p>
                      )}
                    <p className="text-xs text-muted-foreground mt-1">
                      {doc.summary || "📄 No summary available"}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-muted-foreground">
                        {formatSize(doc.file_size)}
                      </span>
                      {doc.status === "ready" && (
                        <>
                          <span className="text-[10px] text-muted-foreground">•</span>
                          <span className="text-[10px] text-muted-foreground">
                            {t("documents.pagesShort", { count: doc.page_count })}
                          </span>
                          <span className="text-[10px] text-muted-foreground">•</span>
                          <span className="text-[10px] text-muted-foreground">
                            {t("documents.chunks", { count: doc.chunk_count })}
                          </span>
                        </>
                      )}
                      {doc.status === "processing" && (
                        <Badge variant="secondary" className="text-[9px] h-4 px-1.5">
                          {t("documents.processing")}
                        </Badge>
                      )}
                      {doc.status === "failed" && (
                        <Badge variant="destructive" className="text-[9px] h-4 px-1.5">
                          {t("documents.failed")}
                        </Badge>
                      )}
                    </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                    {/* Action buttons (Settings and Delete) are only visible on hover and when the document is ready. The settings button is disabled if the document is not ready, and the delete button shows a loader when the document is being deleted. */} 
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                      onClick={(e) => handleSettingsClick(doc, e)}
                      disabled={doc.status !== "ready"}
                    >
                      <Settings className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 cursor-pointer"
                      onClick={(e) => handleDelete(doc.id, e)}
                      disabled={deleting === doc.id}
                    >
                      {deleting === doc.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Trash2 className="w-3 h-3 text-destructive" />
                      )}
                    </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
      {/* Settings Modal */}
      {/* The DocumentSettings component is rendered here and controlled by the settingsDoc state. When a user clicks the settings button for a document, it sets that document in settingsDoc, which opens the modal. The modal can then call onDocumentsChange to refresh the list after saving settings. */}
      {settingsDoc && (
        <DocumentSettings
          document={settingsDoc} // Pass the selected document to the document settings component
          open={!!settingsDoc} // Open when settingsDoc is not null
          onOpenChange={(open) => { // Close the modal when open is false
            if (!open) setSettingsDoc(null); // Clear the settingsDoc state to close the modal
          }}
          onSettingsSaved={() => { // Refresh documents after saving settings
            onDocumentsChange(); // Refresh the document list to reflect any changes
            setSettingsDoc(null); // Close the settings modal after saving
          }}
        />
      )}
    </div>
  );
}
