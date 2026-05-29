"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { Key, Plus, Trash2, Copy, Check } from "lucide-react";

interface ApiKey {
  id: string;
  key_prefix: string;
  created_at: string;
  last_used: string | null;
}

export default function ApiKeyManager() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const data = await api.get<ApiKey[]>("/api/v1/auth/api-keys");
      setKeys(data || []);
    } catch (err) {
      console.error("Failed to load API keys", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const generateKey = async () => {
    try {
      setLoading(true);
      const data = await api.post<{ key: string; api_key: ApiKey }>("/api/v1/auth/api-keys");
      setNewKey(data.key);
      setKeys((prev) => [...prev, data.api_key]);
    } catch (err) {
      console.error("Failed to generate API key", err);
    } finally {
      setLoading(false);
    }
  };

  const revokeKey = async (id: string) => {
    if (!confirm("Are you sure you want to revoke this key? Any integrations using it will immediately break.")) return;
    
    try {
      await api.delete(`/api/v1/auth/api-keys/${id}`);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } catch (err) {
      console.error("Failed to revoke API key", err);
    }
  };

  const copyToClipboard = () => {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Dialog onOpenChange={(open) => { if (!open) setNewKey(null); }}>
      <DialogTrigger className="flex w-full cursor-pointer items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground">
        <Key className="mr-2 h-4 w-4" />
        <span>API Keys</span>
      </DialogTrigger>
      <DialogContent className="max-w-2xl sm:rounded-2xl border-border/40 p-6 md:p-8 bg-background/95 backdrop-blur-xl shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold tracking-tight">API Keys</DialogTitle>
          <p className="text-sm text-muted-foreground mt-1.5">
            Manage API keys to access the RAG engine programmatically from your own applications or scripts.
          </p>
        </DialogHeader>

        {newKey && (
          <div className="my-6 p-5 border border-primary/20 bg-primary/5 rounded-xl space-y-3 animate-in fade-in zoom-in-95 duration-300">
            <h4 className="font-semibold text-primary flex items-center gap-2">
              <Key className="w-4 h-4" /> Save your new API key
            </h4>
            <p className="text-sm text-muted-foreground">
              Please copy this key and store it somewhere safe. For security reasons, you will <strong>never</strong> be able to view it again.
            </p>
            <div className="flex items-center gap-2 mt-2">
              <code className="flex-1 bg-background/80 border border-border/50 px-4 py-2.5 rounded-lg text-sm font-mono break-all text-foreground shadow-inner">
                {newKey}
              </code>
              <Button onClick={copyToClipboard} variant={copied ? "default" : "secondary"} className="shrink-0 shadow-sm">
                {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                {copied ? "Copied!" : "Copy"}
              </Button>
            </div>
          </div>
        )}

        <div className="space-y-4 mt-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-foreground/80 uppercase tracking-wider">Active Keys</h3>
            <Button onClick={generateKey} disabled={loading} size="sm" className="rounded-full shadow-sm hover:shadow-md transition-shadow">
              <Plus className="w-4 h-4 mr-1.5" />
              Generate New Key
            </Button>
          </div>

          <div className="rounded-xl border border-border/50 bg-card overflow-hidden shadow-sm">
            {keys.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground bg-muted/20">
                <Key className="w-8 h-8 mx-auto mb-3 opacity-20" />
                You don&apos;t have any API keys yet.
              </div>
            ) : (
              <div className="divide-y divide-border/50">
                {keys.map((key) => (
                  <div key={key.id} className="flex items-center justify-between p-4 hover:bg-muted/30 transition-colors group">
                    <div className="space-y-1">
                      <div className="font-mono text-sm font-medium tracking-tight">
                        {key.key_prefix}••••••••••••••••••••••
                      </div>
                      <div className="text-xs text-muted-foreground flex gap-4">
                        <span>Created: {new Date(key.created_at).toLocaleDateString()}</span>
                        <span>Last used: {key.last_used ? new Date(key.last_used).toLocaleDateString() : "Never"}</span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => revokeKey(key.id)}
                      className="text-destructive/70 hover:text-destructive hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all"
                      title="Revoke key"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
