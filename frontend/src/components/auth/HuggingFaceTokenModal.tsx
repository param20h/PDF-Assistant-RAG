"use client";

import { useState, useRef, useEffect, isValidElement, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAuthStore } from "@/store/auth-store";
import { Eye, EyeOff, AlertCircle, CheckCircle2, Loader2, ExternalLink, Key } from "lucide-react";

interface HuggingFaceTokenModalProps {
  /** Optional — if provided, allows a button-triggered dialog pattern */
  children?: ReactNode;
}

export default function HuggingFaceTokenModal({ children }: HuggingFaceTokenModalProps) {
  const user = useAuthStore((state) => state.user);
  const setHfToken = useAuthStore((state) => state.setHfToken);

  const existingToken = user?.hf_token ?? "";
  const hasExistingToken = existingToken.length > 0;

  const [open, setOpen] = useState(false);
  const [inputToken, setInputToken] = useState(existingToken);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [showToken, setShowToken] = useState(false);

  const mountedRef = useRef(true);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup auto-close timeout and unmount guard on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, []);

  const clearAutoCloseTimeout = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    clearAutoCloseTimeout();
    setOpen(newOpen);
    if (newOpen) {
      // Reset to current store value when opening (picks up changes from background saves)
      const currentToken = useAuthStore.getState().user?.hf_token ?? "";
      setInputToken(currentToken);
      setSaving(false);
      setError(null);
      setSuccess(false);
      setShowToken(false);
    }
  };

  const handleSave = async () => {
    if (saving) return;
    const token = inputToken.trim();
    if (!token) {
      setError("Please enter a valid token");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await setHfToken(token);
      if (!mountedRef.current) return;
      setSaving(false);
      setSuccess(true);
      // Auto-close after 1.5s
      timeoutRef.current = setTimeout(() => setOpen(false), 1500);
    } catch (err) {
      if (!mountedRef.current) return;
      setSaving(false);
      setError(err instanceof Error ? err.message : "Failed to save token");
    }
  };

  const isSaveDisabled = inputToken.trim() === "" || saving;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {children ? (
        <DialogTrigger render={isValidElement(children) ? children : <span>{children}</span>} />
      ) : (
        <DialogTrigger
          render={
            <button className="flex w-full cursor-pointer items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground">
              <Key className="mr-2 h-4 w-4" />
              <span>HuggingFace Token</span>
            </button>
          }
        />
      )}
      <DialogContent className="max-w-md sm:rounded-2xl border-border/40 p-6 md:p-8 bg-background/95 backdrop-blur-xl shadow-2xl" showCloseButton={false}>
        <DialogHeader className="gap-1">
          <DialogTitle className="text-2xl font-bold tracking-tight">
            🤗 HuggingFace Token
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground mt-1.5">
            Enter your HuggingFace API token to enable inference endpoints and model access.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={(e) => { e.preventDefault(); if (!isSaveDisabled) handleSave(); }}>
        <div className="space-y-4 mt-6">
          {/* Token label with configured indicator */}
          <div className="flex items-center gap-2">
            <label htmlFor="hf-token-input" className="text-sm font-medium text-foreground/80">
              Token
            </label>
            {hasExistingToken && (
              <span className="inline-flex items-center gap-1 text-xs text-primary">
                <CheckCircle2 className="w-3 h-3" />
                Token configured
              </span>
            )}
          </div>

          {/* Input wrapper with visibility toggle */}
          <div className="relative">
            <Input
              id="hf-token-input"
              type={showToken ? "text" : "password"}
              value={inputToken}
              onChange={(e) => {
                setInputToken(e.target.value);
                if (error) setError(null);
                if (success) setSuccess(false);
              }}
              placeholder="hf_..."
              className="pr-10 font-mono"
              disabled={saving}
              autoFocus
              aria-label="HuggingFace API Token"
            />
            <Button
              variant="ghost"
              size="icon-xs"
              className="absolute right-2 top-1/2 -translate-y-1/2"
              onClick={() => setShowToken(!showToken)}
              type="button"
              aria-label={showToken ? "Hide token" : "Show token"}
              disabled={saving}
            >
              {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </Button>
          </div>

          {/* External link */}
          <a
            href="https://huggingface.co/settings/tokens"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground hover:text-primary underline-offset-2 transition-colors inline-flex items-center gap-1"
          >
            <ExternalLink className="w-3 h-3" />
            Get your API token from HuggingFace Settings
          </a>
        </div>

        {/* Error banner */}
        {error && (
          <div
            className="p-4 border border-destructive/30 bg-destructive/5 rounded-xl text-sm text-destructive flex items-start gap-2 mt-4 animate-in fade-in slide-in-from-top-2 duration-200"
            role="alert"
            aria-live="polite"
          >
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Success banner */}
        {success && (
          <div
            className="p-4 border border-primary/20 bg-primary/5 rounded-xl text-sm text-primary flex items-start gap-2 mt-4 animate-in fade-in slide-in-from-top-2 duration-200"
            aria-live="polite"
          >
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            <span>Token saved successfully</span>
          </div>
        )}
        </form>

        {/* Footer */}
        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaveDisabled}
            aria-busy={saving}
            title={hasExistingToken ? "Replace existing token with a new one" : undefined}
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-1.5" />
                Saving...
              </>
            ) : hasExistingToken ? (
              "Update Token"
            ) : (
              "Save Token"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
