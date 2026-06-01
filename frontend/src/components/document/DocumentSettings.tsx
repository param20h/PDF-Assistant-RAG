"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertCircle, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import type { DocInfo } from "@/app/dashboard/page";

interface Props {
  document: DocInfo;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSettingsSaved: () => void;
}

const DEFAULT_CHUNK_SIZE = 1000;
const DEFAULT_CHUNK_OVERLAP = 200;

// This component holds the form state and logic. It is recreated (via key) each time the modal opens or the document changes.
function DocumentSettingsBody({
  document,
  onOpenChange,
  onSettingsSaved,
}: Pick<Props, "document" | "onOpenChange" | "onSettingsSaved">) {
  // Local state for chunk size, overlap, loading status, and error messages. Initialized with document settings or defaults. This state is used to control the form inputs and display feedback to the user.
  const [chunkSize, setChunkSize] = useState<number>(
    document.chunk_size ?? DEFAULT_CHUNK_SIZE
  );
  const [chunkOverlap, setChunkOverlap] = useState<number>(
    document.chunk_overlap ?? DEFAULT_CHUNK_OVERLAP
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  {/* validates the input values and calls the API to save the new settings. It also handles loading state and displays any errors that occur during the API call. On success, it notifies the parent component to refresh the document data and closes the modal. */}
  const handleSave = async () => {
    if (chunkSize < 100) return setError("Chunk size must be at least 100 characters");
    if (chunkSize > 4000) return setError("Chunk size cannot exceed 4000 characters (LLM token limit)");
    if (chunkOverlap < 0) return setError("Overlap cannot be negative");
    if (chunkOverlap >= chunkSize) return setError("Overlap must be less than chunk size");

    setLoading(true); // Set loading state to disable inputs and show progress
    setError(null); // Clear any existing errors before API call
    try { // Call API to update chunk settings for the document
      await api.post(`/api/v1/documents/${document.id}/chunk_settings`, {
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      });
      onSettingsSaved(); // Notify parent to refresh document data 
      onOpenChange(false); // Close modal on success
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update settings"); 
    } finally {
      setLoading(false); // Reset loading state after API call completes
    }
  };

  {/* Resets the chunk size and overlap to their default values and clears any error messages. This allows users to quickly revert to recommended settings if they encounter issues. */}
  const handleReset = () => {
    setChunkSize(DEFAULT_CHUNK_SIZE);
    setChunkOverlap(DEFAULT_CHUNK_OVERLAP);
    setError(null);
  };

  {/* The modal dialog component that contains the form for adjusting chunking settings. It includes input sliders for chunk size and overlap, displays current values, and shows validation errors or warnings. The save button triggers the handleSave function, while the reset button reverts to default settings. The modal is controlled by the 'open' prop and can be closed by clicking outside or using the cancel button. */}
  return (
    <DialogContent className="max-w-xl">
      <DialogHeader>
        <DialogTitle>Chunking Settings</DialogTitle>
        <DialogDescription>Adjust how the document is split before embedding.</DialogDescription>
      </DialogHeader>

      <div className="space-y-5 py-2">
        {/* Displays chunk size details when hovered on special symbol */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-medium">Chunk size</span>
              <span
                className="text-xs text-muted-foreground cursor-help"
                title="Maximum characters per chunk. Larger chunks preserve more context but cost more."
              >
                ⓘ
              </span>
            </div>
            <span className="text-sm font-mono">{chunkSize} chars</span>
          </div>
          {/* The chunk size input is a range slider that allows users to select a value between 200 and 4000 characters. If the selected chunk size exceeds 3000 characters, a warning message is shown to inform users about potential increased processing time. */}
          <input
            type="range"
            min={200}
            max={4000}
            step={50}
            value={chunkSize}
            onChange={(e) => setChunkSize(Number(e.target.value))}
            className="w-full accent-primary cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>200</span>
            <span>1000</span>
            <span>4000</span>
          </div>
          {chunkSize > 3000 && (
            <p className="text-xs text-yellow-600 dark:text-yellow-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              May increase processing time
            </p>
          )}
        </div>

        {/* Displays chunk overlap details when hovered on special symbol */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-medium">Overlap</span>
              <span
                className="text-xs text-muted-foreground cursor-help"
                title="Characters overlapped between consecutive chunks. Helps maintain context across boundaries."
              >
                ⓘ
              </span>
            </div>
            <span className="text-sm font-mono">{chunkOverlap} chars</span>
          </div>
          {/* The chunk overlap input is a range slider that allows users to select a value between 0 and the maximum allowed based on the current chunk size. If the selected overlap exceeds half of the chunk size, a warning message is displayed to inform users about potential duplicate chunks. */}
          <input
            type="range"
            min={0}
            max={Math.max(0, chunkSize - 50)}
            step={25}
            value={chunkOverlap}
            onChange={(e) => setChunkOverlap(Number(e.target.value))}
            disabled={chunkSize <= 50}
            className="w-full accent-primary disabled:opacity-50 cursor-pointer"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0</span>
            <span>200</span>
            <span>{chunkSize - 50}</span>
          </div>
          {chunkOverlap > chunkSize / 2 && (
            <p className="text-xs text-yellow-600 dark:text-yellow-400 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              High overlap creates duplicate chunks
            </p>
          )}
        </div>

        {/* If there is an error message in the state, it is displayed in a styled div with a red background and an alert icon. */}
        {error && (
          <div className="p-2 rounded-md bg-destructive/10 text-sm text-destructive flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

         {/* Action buttons for resetting to default settings, canceling changes, and saving new settings. The save button triggers the handleSave function, while the reset button reverts to default values. Both buttons are disabled when the loading state is true to prevent multiple submissions. A note is displayed below the buttons to inform users that changing settings will re-chunk and re-embed the entire document. */}
        <div className="flex justify-between items-center pt-2">
          <Button variant="outline" size="sm" onClick={handleReset} disabled={loading} className="cursor-pointer">
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
            Reset
          </Button>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)} className="cursor-pointer">
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave} disabled={loading} className="cursor-pointer">
              {loading ? "Saving..." : "Save & Re-index"}
            </Button>
          </div>
        </div>

        <p className="text-[11px] text-muted-foreground text-center">
          Changing these settings will re-chunk and re-embed the entire document.
        </p>
      </div>
    </DialogContent>
  );
}

// Main modal component – controls the Dialog and forces a remount of the body when needed.
export default function DocumentSettingsModal({
  document,
  open,
  onOpenChange,
  onSettingsSaved,
}: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}> 
    {/*The Dialog component from the UI library that wraps the content of the modal. It takes 'open' and 'onOpenChange' props to control its visibility. When 'open' is true, the modal is displayed, and 'onOpenChange' is called with the new open state when the user attempts to close the modal (e.g., by clicking outside or pressing the escape key). The DocumentSettingsBody component is rendered inside the Dialog, and it receives the current document and callback functions as props. The key prop on DocumentSettingsBody ensures that it remounts with fresh state each time the modal is opened or a different document is selected. */}
      {open && (
        <DocumentSettingsBody
          key={`${document.id}-${open ? "open" : "closed"}`} // Force remount to reset internal state when document or open state changes
          document={document}
          onOpenChange={onOpenChange}
          onSettingsSaved={onSettingsSaved}
        />
      )}
    </Dialog>
  );
}