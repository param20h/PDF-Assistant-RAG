"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Brain, CheckCircle2, AlertTriangle, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { useWorkspaceStore } from "@/store/workspace-store";

interface InviteInfo {
  workspace_name: string;
  inviter_email: string;
  inviter_username: string;
  email: string;
  expires_at: string;
  is_expired: boolean;
  is_accepted: boolean;
}

function InviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, initialized } = useAuth();
  const setWorkspace = useWorkspaceStore((s) => s.setWorkspace);
  
  const token = searchParams.get("token");
  
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState("");
  const [inviteInfo, setInviteInfo] = useState<InviteInfo | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Invitation token is missing. Please check the link in your email.");
      setLoading(false);
      return;
    }

    // Save token to sessionStorage in case they need to log in/register
    try {
      sessionStorage.setItem("pending_invite_token", token);
    } catch (e) {
      console.warn("sessionStorage is not available", e);
    }

    api
      .get<InviteInfo>(`/api/v1/workspaces/invite/verify?token=${encodeURIComponent(token)}`)
      .then((data) => {
        setInviteInfo(data);
        if (data.is_expired) {
          setError(`This invitation has expired (expired at ${new Date(data.expires_at).toLocaleString()}).`);
        } else if (data.is_accepted) {
          setError("This invitation has already been accepted.");
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to verify invitation token.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  const handleAccept = async () => {
    if (!token) return;
    setAccepting(true);

    try {
      await api.post(`/api/v1/workspaces/invite/accept?token=${encodeURIComponent(token)}`);
      toast.success(`🎉 Welcome to the '${inviteInfo?.workspace_name}' workspace!`);
      
      // Clean up sessionStorage
      try {
        sessionStorage.removeItem("pending_invite_token");
      } catch (e) {
        // ignore
      }

      // Switch to company workspace in store so they see the documents immediately
      setWorkspace("company");
      
      router.push("/dashboard");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to accept invitation.");
      setAccepting(false);
    }
  };

  if (loading || !initialized) {
    return (
      <div className="flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-12 h-12 text-primary animate-spin" />
        <p className="text-sm text-muted-foreground">Verifying invitation details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="w-full max-w-md bg-card/85 backdrop-blur-xl border-destructive/30 shadow-lg relative z-10 animate-fade-in-up">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-xl bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-destructive" />
            </div>
          </div>
          <CardTitle className="text-xl font-bold text-destructive">Invitation Error</CardTitle>
          <CardDescription className="mt-2 text-sm">{error}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center pt-4">
          <Button onClick={() => router.push("/dashboard")} className="w-full">
            Go to Dashboard
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isLoggedIn = !!user;

  return (
    <Card className="w-full max-w-md bg-card/80 backdrop-blur-xl border-border/50 shadow-2xl relative z-10 animate-fade-in-up">
      <CardHeader className="text-center pb-2">
        <div className="flex justify-center mb-4">
          <div className="w-12 h-12 rounded-xl bg-primary/15 flex items-center justify-center">
            <Brain className="w-6 h-6 text-primary animate-pulse" />
          </div>
        </div>
        <CardTitle className="text-2xl font-bold text-foreground">Workspace Invitation</CardTitle>
        <CardDescription className="text-sm mt-1">
          You've been invited to join a collaborative workspace
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6 pt-2">
        <div className="rounded-xl bg-muted/50 border border-border/40 p-4 text-center space-y-2">
          <p className="text-xs text-muted-foreground uppercase font-semibold tracking-wider">Workspace</p>
          <p className="text-lg font-bold text-foreground">{inviteInfo?.workspace_name}</p>
          <p className="text-xs text-muted-foreground">
            Invited by <span className="font-medium text-foreground">{inviteInfo?.inviter_username}</span> ({inviteInfo?.inviter_email})
          </p>
        </div>

        {isLoggedIn ? (
          <div className="space-y-3">
            <p className="text-xs text-center text-muted-foreground">
              You are logged in as <span className="font-medium text-foreground">{user.username}</span> ({user.email}).
            </p>
            <Button 
              onClick={handleAccept} 
              disabled={accepting} 
              className="w-full h-11 text-base font-semibold cursor-pointer"
            >
              {accepting ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Accepting...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Accept & Join Workspace
                </span>
              )}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-xs text-yellow-500 text-center">
              Please log in or register an account to accept this invitation.
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Button 
                variant="outline" 
                onClick={() => router.push("/login")} 
                className="h-11 font-medium cursor-pointer"
              >
                Log In
              </Button>
              <Button 
                onClick={() => router.push("/register")} 
                className="h-11 font-medium cursor-pointer"
              >
                Sign Up <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function InvitePage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden bg-background">
      {/* Aesthetic blur gradients */}
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-500/8 rounded-full blur-[120px] pointer-events-none" />
      
      <Suspense fallback={
        <div className="flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-12 h-12 text-primary animate-spin" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      }>
        <InviteContent />
      </Suspense>
    </div>
  );
}
