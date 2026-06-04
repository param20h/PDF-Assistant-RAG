"use client";

import { AlertTriangle, X } from "lucide-react";
import { useEffect, useRef } from "react";

interface Props {
  filename: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  errorMessage?: string | null;
}

export function ConfirmReplaceModal({
  filename,
  onConfirm,
  onCancel,
  isLoading = false,
  errorMessage = null,
}: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Focus cancel by default (safe option)
  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="replace-modal-title"
        className="
          fixed z-50 left-1/2 top-1/2
          -translate-x-1/2 -translate-y-1/2
          w-full max-w-md
          bg-white dark:bg-gray-900
          rounded-2xl shadow-2xl
          border border-gray-200 dark:border-gray-700
          p-6
        "
      >
        {/* Close × */}
        <button
          onClick={onCancel}
          className="
            absolute top-4 right-4
            p-1 rounded-md text-gray-400
            hover:text-gray-600 dark:hover:text-gray-200
            hover:bg-gray-100 dark:hover:bg-gray-800
            transition-colors
          "
          aria-label="Cancel"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Icon + heading */}
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h2
              id="replace-modal-title"
              className="text-base font-semibold text-gray-900 dark:text-gray-100"
            >
              Replace existing document?
            </h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              <span className="font-medium text-gray-900 dark:text-gray-100">
                &ldquo;{filename}&rdquo;
              </span>{" "}
              already exists. Replacing it will permanently remove the existing
              document and its entire chat history.
            </p>
          </div>
        </div>

        {/* Locked / error message */}
        {errorMessage && (
          <div className="mt-4 px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-700 dark:text-red-400">
              {errorMessage}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            ref={cancelRef}
            onClick={onCancel}
            disabled={isLoading}
            className="
              px-4 py-2 rounded-lg text-sm font-medium
              bg-gray-100 text-gray-700
              dark:bg-gray-800 dark:text-gray-300
              hover:bg-gray-200 dark:hover:bg-gray-700
              disabled:opacity-50
              transition-colors
            "
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="
              px-4 py-2 rounded-lg text-sm font-medium
              bg-red-600 text-white
              hover:bg-red-700
              disabled:opacity-60
              transition-colors
              flex items-center gap-2
            "
          >
            {isLoading && (
              <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            )}
            {isLoading ? "Replacing…" : "Replace"}
          </button>
        </div>
      </div>
    </>
  );
}
