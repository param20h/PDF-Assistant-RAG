/**
 * useDashboardDrop
 *
 * Tracks when the user drags files over the browser window and exposes
 * an `isDraggingOver` flag so the dashboard can render a full-page
 * drop-zone overlay. The actual file handling is delegated to the
 * caller via `onDrop`.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"];
const ACCEPTED_MIME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
];

function hasAcceptedFile(transfer: DataTransfer): boolean {
  // DataTransferItemList gives MIME type before the drop
  if (transfer.items && transfer.items.length > 0) {
    return Array.from(transfer.items).some(
      (item) => item.kind === "file" && ACCEPTED_MIME_TYPES.includes(item.type),
    );
  }
  // Fallback: FileList (available after drop)
  if (transfer.files && transfer.files.length > 0) {
    return Array.from(transfer.files).some((file) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      return ACCEPTED_EXTENSIONS.includes(ext);
    });
  }
  return false;
}

interface UseDashboardDropOptions {
  onDrop: (files: File[]) => void;
  disabled?: boolean;
}

interface UseDashboardDropResult {
  isDraggingOver: boolean;
  dropZoneProps: {
    onDragEnter: (e: React.DragEvent) => void;
    onDragOver: (e: React.DragEvent) => void;
    onDragLeave: (e: React.DragEvent) => void;
    onDrop: (e: React.DragEvent) => void;
  };
}

export function useDashboardDrop({
  onDrop,
  disabled = false,
}: UseDashboardDropOptions): UseDashboardDropResult {
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  // Counter tracks nested dragenter/dragleave pairs so we don't flicker
  const dragCounter = useRef(0);

  const handleWindowDragEnter = useCallback(
    (e: DragEvent) => {
      if (disabled) return;
      if (!e.dataTransfer || !hasAcceptedFile(e.dataTransfer)) return;
      dragCounter.current += 1;
      if (dragCounter.current === 1) setIsDraggingOver(true);
    },
    [disabled],
  );

  const handleWindowDragLeave = useCallback(
    (e: DragEvent) => {
      if (disabled) return;
      dragCounter.current = Math.max(0, dragCounter.current - 1);
      if (dragCounter.current === 0) setIsDraggingOver(false);
    },
    [disabled],
  );

  const handleWindowDrop = useCallback((e: DragEvent) => {
    dragCounter.current = 0;
    setIsDraggingOver(false);
  }, []);

  // Attach window-level listeners so ANY drag over the page triggers the overlay
  useEffect(() => {
    window.addEventListener("dragenter", handleWindowDragEnter);
    window.addEventListener("dragleave", handleWindowDragLeave);
    window.addEventListener("drop", handleWindowDrop);
    return () => {
      window.removeEventListener("dragenter", handleWindowDragEnter);
      window.removeEventListener("dragleave", handleWindowDragLeave);
      window.removeEventListener("drop", handleWindowDrop);
    };
  }, [handleWindowDragEnter, handleWindowDragLeave, handleWindowDrop]);

  // Reset when disabled
  useEffect(() => {
    if (disabled) {
      dragCounter.current = 0;
      const id = setTimeout(() => setIsDraggingOver(false), 0);
      return () => clearTimeout(id);
    }
  }, [disabled]);

  // Props spread onto the overlay <div> itself
  const dropZoneProps = {
    onDragEnter: (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    },
    onDragOver: (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "copy";
    },
    onDragLeave: (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    },
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setIsDraggingOver(false);
      if (disabled) return;

      const files = Array.from(e.dataTransfer.files).filter((file) => {
        const ext = "." + file.name.split(".").pop()?.toLowerCase();
        return ACCEPTED_EXTENSIONS.includes(ext);
      });

      if (files.length > 0) {
        onDrop(files);
      }
    },
  };

  return { isDraggingOver, dropZoneProps };
}
