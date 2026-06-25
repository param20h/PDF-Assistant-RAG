"use client";

import { Trash2, X, RotateCcw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface BulkActionBarProps {
  selectedCount: number;
  onDelete: () => void;
  onRestore?: () => void;
  onClear: () => void;
  deleting: boolean;
  restoring?: boolean;
  mode?: "active" | "trash";
}

export default function BulkActionBar({
  selectedCount,
  onDelete,
  onRestore,
  onClear,
  deleting,
  restoring = false,
  mode = "active",
}: BulkActionBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div
      role="toolbar"
      aria-label="Bulk document actions"
      className="flex items-center justify-between gap-2 px-3 py-2 bg-primary/10 border-b border-primary/20 animate-in slide-in-from-top-1 duration-150"
    >
      <span className="text-xs font-medium text-primary">
        {selectedCount} selected
      </span>

      <div className="flex items-center gap-1">
        {mode === "trash" && onRestore && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs gap-1.5 text-primary hover:text-primary hover:bg-primary/10"
            onClick={onRestore}
            disabled={restoring || deleting}
            aria-label={`Restore ${selectedCount} selected documents`}
          >
            {restoring ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <RotateCcw className="w-3 h-3" />
            )}
            Restore
          </Button>
        )}

        {mode === "active" && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs gap-1.5 text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={onDelete}
            disabled={deleting || restoring}
            aria-label={`Delete ${selectedCount} selected documents`}
          >
            {deleting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Trash2 className="w-3 h-3" />
            )}
            Delete
          </Button>
        )}

        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onClear}
          disabled={deleting || restoring}
          aria-label="Clear selection"
        >
          <X className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
}
