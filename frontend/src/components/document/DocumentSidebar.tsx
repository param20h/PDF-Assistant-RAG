"use client";

import { useState, useCallback } from "react";
import type { DocInfo } from "@/app/dashboard/page";
import { api } from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  FileText, Upload, Trash2, FileCheck, Clock, AlertCircle, Loader2, FolderOpen,
} from "lucide-react";
import { useDropzone } from "react-dropzone";

interface Props {
  documents: DocInfo[];
  activeDoc: DocInfo | null;
  onSelectDoc: (doc: DocInfo) => void;
  onDocumentsChange: () => void;
}

export default function DocumentSidebar({ documents, activeDoc, onSelectDoc, onDocumentsChange }: Props) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [deleting, setDeleting] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      setUploading(true);
      setUploadProgress(0);

      try {
        for (let i = 0; i < acceptedFiles.length; i++) {
          const formData = new FormData();
          formData.append("file", acceptedFiles[i]);
          await api.postForm("/api/v1/documents/upload", formData);
          setUploadProgress(((i + 1) / acceptedFiles.length) * 100);
        }
        onDocumentsChange();
      } catch (err) {
        console.error("Upload failed:", err);
      } finally {
        setUploading(false);
        setUploadProgress(0);
      }
    },
    [onDocumentsChange]
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
    if (!confirm("Delete this document and all its data?")) return;
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
      <div className="p-3 border-b border-sidebar-border">
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
              <p className="text-xs text-muted-foreground">Uploading...</p>
              <Progress value={uploadProgress} className="h-1" />
            </div>
          ) : (
            <>
              <Upload className="w-5 h-5 mx-auto text-muted-foreground mb-2" />
              <p className="text-xs text-muted-foreground">
                {isDragActive ? "Drop files here" : "Drop files or click to upload"}
              </p>
              <p className="text-[10px] text-muted-foreground/60 mt-1">
                PDF, DOCX, TXT, MD (max 50MB)
              </p>
            </>
          )}
        </div>
      </div>

      {/* ── Documents List ──────────────────────────── */}
      <div className="px-3 pt-3 pb-1">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Documents ({documents.length})
        </h3>
      </div>

      <ScrollArea className="flex-1 px-3">
        {documents.length === 0 ? (
          <div className="text-center py-12">
            <FolderOpen className="w-8 h-8 mx-auto text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">No documents yet</p>
            <p className="text-xs text-muted-foreground/60 mt-1">Upload a file to get started</p>
          </div>
        ) : (
          <div className="space-y-1 pb-3">
            {documents.map((doc) => (
              <button
                key={doc.id}
                onClick={() => doc.status === "ready" && onSelectDoc(doc)}
                className={`w-full text-left p-2.5 rounded-lg transition-all duration-200 group
                  ${activeDoc?.id === doc.id
                    ? "bg-primary/15 border border-primary/30"
                    : "hover:bg-sidebar-accent border border-transparent"}
                  ${doc.status !== "ready" ? "opacity-60 cursor-default" : "cursor-pointer"}`}
              >
                <div className="flex items-start gap-2.5">
                  {statusIcon(doc.status)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate leading-tight">
                      {doc.original_name}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-muted-foreground">
                        {formatSize(doc.file_size)}
                      </span>
                      {doc.status === "ready" && (
                        <>
                          <span className="text-[10px] text-muted-foreground">•</span>
                          <span className="text-[10px] text-muted-foreground">
                            {doc.page_count} pg
                          </span>
                          <span className="text-[10px] text-muted-foreground">•</span>
                          <span className="text-[10px] text-muted-foreground">
                            {doc.chunk_count} chunks
                          </span>
                        </>
                      )}
                      {doc.status === "processing" && (
                        <Badge variant="secondary" className="text-[9px] h-4 px-1.5">
                          Processing
                        </Badge>
                      )}
                      {doc.status === "failed" && (
                        <Badge variant="destructive" className="text-[9px] h-4 px-1.5">
                          Failed
                        </Badge>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
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
              </button>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
