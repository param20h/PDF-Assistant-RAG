"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";
import HuggingFaceTokenModal from "@/components/auth/HuggingFaceTokenModal";
import { CheckCircle2, XCircle, Settings, Key } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function SettingsPage() {
  const { user, initialized } = useAuth();
  const router = useRouter();

  const hfToken = useAuthStore((s) => s.user?.hf_token ?? "");
  const isConnected = hfToken.trim().length > 0;

  useEffect(() => {
    if (initialized && !user) router.replace("/login");
  }, [user, initialized, router]);

  if (!initialized || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse w-12 h-12 rounded-full bg-primary/20" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="h-14 flex items-center gap-3 px-6 border-b border-border/50 bg-card/50 backdrop-blur-md">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 hover:opacity-75 transition-opacity"
          aria-label="Back to dashboard"
        >
          <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
            <Settings className="w-4 h-4 text-primary" />
          </div>
          <span className="font-semibold text-sm">Settings</span>
        </Link>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-10 space-y-8">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your account and integrations.
          </p>
        </div>

        <section className="rounded-xl border border-border/50 bg-card/50 p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-primary" />
            <h2 className="font-semibold text-base">HuggingFace Token</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Connect your HuggingFace API token to enable inference endpoints and model access.
          </p>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span className="text-sm text-green-600 dark:text-green-400 font-medium">Connected</span>
                <span className="text-xs text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded">
                  {hfToken.slice(0, 6)}••••••••
                </span>
              </>
            ) : (
              <>
                <XCircle className="w-4 h-4 text-destructive" />
                <span className="text-sm text-destructive font-medium">Not connected</span>
              </>
            )}
          </div>
          <HuggingFaceTokenModal>
            <Button variant="outline" size="sm">
              {isConnected ? "Update Token" : "Connect Token"}
            </Button>
          </HuggingFaceTokenModal>
        </section>

        <section className="rounded-xl border border-border/50 bg-card/50 p-6 space-y-4">
          <h2 className="font-semibold text-base">Account</h2>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Username</p>
            <p className="text-sm font-medium">{user.username}</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Email</p>
            <p className="text-sm font-medium">{user.email}</p>
          </div>
        </section>
      </main>
    </div>
  );
}
