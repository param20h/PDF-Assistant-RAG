"use client";

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useDropzone } from "react-dropzone";
import { Upload, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import { ConfirmReplaceModal } from "./ConfirmReplaceModal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface Props {
  onDocumentsChange: () => void;
}

export default function DocumentUpload({ onDocumentsChange }: Props) {
  const { t } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState("");
  const [conflictMeta, setConflictMeta] = useState<{
    existingId: number | string;
    filename: string;
    formData: FormData;
  } | null>(null);
  const [replaceLoading, setReplaceLoading] = useState(false);
  const [replaceError, setReplaceError] = useState<string | null>(null);

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const refreshDocuments = useCallback(() => {
    onDocumentsChange();
  }, [onDocumentsChange]);

  const handleReplace = useCallback(async () => {
    if (!conflictMeta) return;
    setReplaceLoading(true);
    setReplaceError(null);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/documents/${conflictMeta.existingId}/replace`,
        {
          method: "PUT",
          headers: { Authorization: `Bearer ${token}` },
          body: conflictMeta.formData,
        }
      );

      if (res.status === 423) {
      setReplaceError(
        "This document is still being processed. Please wait before replacing it."
      );
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setReplaceError(body.detail ?? "Replace failed. Please try again.");
        return;
      }

      setConflictMeta(null);
      await refreshDocuments();
    } finally {
      setReplaceLoading(false);
    }
  }, [conflictMeta, token, refreshDocuments]);

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

            const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` },
              body: formData,
            });

            if (res.status === 409) {
              const body = await res.json();
              setConflictMeta({
                existingId: body.detail.existing_id,
                filename: body.detail.original_name,
                formData,
              });
              return;
            }

            if (!res.ok) {
              const body = await res.json().catch(() => ({}));
              toast.error(body.detail ?? "Upload failed. Please try again.");
              return;
            }

            setUploadProgress(((i + 1) / acceptedFiles.length) * 100);
            toast.success(
              `📤 '${file.name}' uploaded successfully! Ingestion started.`
            );
          }
          onDocumentsChange();
        } catch (err) {
          const message =
            err instanceof Error ? err.message : t("documents.uploadFailed");
          setUploadError(message);
          toast.error(`❌ Upload failed: ${message}`);
        } finally {
          setUploading(false);
          setUploadProgress(0);
        }
      })();
    },
    [onDocumentsChange, t, token]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        ".docx",
      ],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
    },
    disabled: uploading,
  });

  return (
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
        aria-label="Upload documents"
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

      {conflictMeta && (
        <ConfirmReplaceModal
          filename={conflictMeta.filename}
          onConfirm={handleReplace}
          onCancel={() => {
            setConflictMeta(null);
            setReplaceError(null);
          }}
          isLoading={replaceLoading}
          errorMessage={replaceError}
        />
      )}
    </div>
  );
}
