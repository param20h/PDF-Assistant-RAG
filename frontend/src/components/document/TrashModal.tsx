"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Trash2, RotateCcw, FileText, Loader2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { DocInfo } from "@/app/dashboard/page";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDocumentsChange: () => void;
}

export default function TrashModal({ open, onOpenChange, onDocumentsChange }: Props) {
  const [trashDocs, setTrashDocs] = useState<DocInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<"restore" | "purge" | null>(null);

  const fetchTrash = async () => {
    setLoading(true);
    try {
      const data = await api.get<DocInfo[]>("/api/v1/documents/trash");
      setTrashDocs(data);
    } catch (err) {
      console.error("Failed to load trash documents:", err);
      toast.error("Failed to load Recycle Bin items");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      void fetchTrash();
    }
  }, [open]);

  const handleRestore = async (doc: DocInfo) => {
    setActionId(doc.id);
    setActionType("restore");
    try {
      await api.post(`/api/v1/documents/${doc.id}/restore`);
      toast.success(`🎉 Restored '${doc.original_name}' successfully!`);
      // Update local state and trigger parent refresh
      setTrashDocs((prev) => prev.filter((d) => d.id !== doc.id));
      onDocumentsChange();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to restore document");
    } finally {
      setActionId(null);
      setActionType(null);
    }
  };

  const handlePurge = async (doc: DocInfo) => {
    if (!confirm(`⚠️ Are you sure you want to permanently delete '${doc.original_name}'? This action is irreversible and will purge all files, vector chunks, and graph data immediately.`)) {
      return;
    }

    setActionId(doc.id);
    setActionType("purge");
    try {
      await api.delete(`/api/v1/documents/${doc.id}/purge`);
      toast.success(`🗑️ Permanently deleted '${doc.original_name}'`);
      setTrashDocs((prev) => prev.filter((d) => d.id !== doc.id));
      onDocumentsChange();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete document");
    } finally {
      setActionId(null);
      setActionType(null);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-card border border-border/80 shadow-2xl backdrop-blur-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-semibold">
            <Trash2 className="w-5 h-5 text-destructive" />
            Recycle Bin
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Items in the Recycle Bin will be permanently purged after 30 days. You can restore them or delete them permanently now.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <ScrollArea className="h-[350px] pr-4">
            {loading && trashDocs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full py-16 space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Loading trashed files...</p>
              </div>
            ) : trashDocs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="p-4 rounded-full bg-muted/40 mb-4">
                  <Trash2 className="w-10 h-10 text-muted-foreground/40" />
                </div>
                <p className="text-sm font-medium">Recycle Bin is empty</p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  Soft-deleted documents will appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {trashDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-border/60 hover:bg-muted/40 transition-colors"
                  >
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <FileText className="w-5 h-5 mt-0.5 text-muted-foreground shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate" title={doc.original_name}>
                          {doc.original_name}
                        </p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <span>{formatSize(doc.file_size)}</span>
                          <span>•</span>
                          <span>Deleted: {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRestore(doc)}
                        disabled={actionId !== null}
                        className="h-8 cursor-pointer text-xs"
                      >
                        {actionId === doc.id && actionType === "restore" ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                        ) : (
                          <RotateCcw className="w-3.5 h-3.5 mr-1" />
                        )}
                        Restore
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handlePurge(doc)}
                        disabled={actionId !== null}
                        className="h-8 hover:bg-destructive/10 text-destructive hover:text-destructive cursor-pointer text-xs"
                      >
                        {actionId === doc.id && actionType === "purge" ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5 mr-1" />
                        )}
                        Purge
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        <div className="flex justify-end gap-2 border-t pt-4">
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
