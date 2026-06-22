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
import { Eye, EyeOff, AlertCircle, CheckCircle2, Loader2, ExternalLink, Key, Trash2 } from "lucide-react";

interface HuggingFaceTokenModalProps {
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
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [showToken, setShowToken] = useState(false);

  const mountedRef = useRef(true);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      const currentToken = useAuthStore.getState().user?.hf_token ?? "";
      setInputToken(currentToken);
      setSaving(false);
      setRemoving(false);
      setError(null);
      setSuccess(false);
      setShowToken(false);
    }
  };

  const validateToken = (token: string): string | null => {
    if (!token) return "Please enter a valid token";
    if (!token.startsWith("hf_")) return "Token must start with 'hf_'";
    if (token.length < 20) return "Token is too short — please check and try again";
    return null;
  };

  const getTokenPreview = (token: string): string => {
    if (token.length <= 8) return token;
    return `${token.slice(0, 7)}****${token.slice(-4)}`;
  };

  const handleSave = async () => {
    if (saving) return;
    const token = inputToken.trim();
    const validationError = validateToken(token);
    if (validationError) {
      setError(validationError);
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
      timeoutRef.current = setTimeout(() => setOpen(false), 1500);
    } catch (err) {
      if (!mountedRef.current) return;
      setSaving(false);
      setError(err instanceof Error ? err.message : "Failed to save token");
    }
  };

  const handleRemove = async () => {
    if (removing) return;
    setRemoving(true);
    setError(null);
    setSuccess(false);
    try {
      await setHfToken("");
      if (!mountedRef.current) return;
      setRemoving(false);
      setInputToken("");
      setSuccess(true);
      timeoutRef.current = setTimeout(() => setOpen(false), 1500);
    } catch (err) {
      if (!mountedRef.current) return;
      setRemoving(false);
      setError(err instanceof Error ? err.message : "Failed to remove token");
    }
  };

  const isSaveDisabled = inputToken.trim() === "" || saving || removing;

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

            {hasExistingToken && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/5 border border-primary/20 text-xs font-mono text-primary">
                <CheckCircle2 className="w-3 h-3 shrink-0" />
                <span>Current: {getTokenPreview(existingToken)}</span>
              </div>
            )}

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
                disabled={saving || removing}
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
                disabled={saving || removing}
              >
                {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              Token must start with{" "}
              <span className="font-mono text-primary">hf_</span>
            </p>

            
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

          {success && (
            <div
              className="p-4 border border-primary/20 bg-primary/5 rounded-xl text-sm text-primary flex items-start gap-2 mt-4 animate-in fade-in slide-in-from-top-2 duration-200"
              aria-live="polite"
            >
              <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{inputToken ? "Token saved successfully" : "Token removed successfully"}</span>
            </div>
          )}
        </form>

        <DialogFooter className="mt-4 flex gap-2">
          {hasExistingToken && (
            <Button
              variant="outline"
              className="text-destructive hover:text-destructive border-destructive/30 hover:bg-destructive/5"
              onClick={handleRemove}
              disabled={removing || saving}
              type="button"
            >
              {removing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-1.5" />
                  Removing...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-1.5" />
                  Remove
                </>
              )}
            </Button>
          )}

          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={saving || removing}
          >
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