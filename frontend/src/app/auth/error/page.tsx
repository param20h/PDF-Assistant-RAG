"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { AlertTriangle, RefreshCcw, Home } from "lucide-react";

const ERROR_MESSAGES: Record<string, { title: string; description: string }> = {
  csrf_mismatch: {
    title: "Security Check Failed",
    description:
      "The OAuth state did not match. This could indicate a CSRF attack. Please try signing in again.",
  },
  token_exchange_failed: {
    title: "Token Exchange Failed",
    description:
      "We could not exchange your authorization code for an access token. Please try again.",
  },
  userinfo_failed: {
    title: "Profile Fetch Failed",
    description:
      "We could not retrieve your Hugging Face profile. Please check your account and try again.",
  },
  email_required: {
    title: "Email Required",
    description:
      "Your Hugging Face account did not provide an email address. Please ensure your email is public and try again.",
  },
  oauth_not_configured: {
    title: "OAuth Not Configured",
    description:
      "Hugging Face OAuth is not configured on this server. Please contact the administrator.",
  },
  default: {
    title: "Authentication Failed",
    description:
      "Something went wrong during sign-in with Hugging Face. Please try again.",
  },
};

function AuthErrorContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const errorCode = searchParams.get("error") ?? "default";
  const { title, description } =
    ERROR_MESSAGES[errorCode] ?? ERROR_MESSAGES.default;

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-destructive/8 rounded-full blur-[100px] pointer-events-none" />

      <Card className="w-full max-w-md relative z-10 bg-card/80 backdrop-blur-xl border-border/50">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-xl bg-destructive/15 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-destructive" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">{title}</CardTitle>
          <CardDescription className="text-sm text-muted-foreground mt-1">
            {description}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-3 pt-2">
          {errorCode !== "default" && (
            <div className="flex justify-center">
              <span className="text-xs font-mono bg-muted px-2 py-1 rounded-md text-muted-foreground">
                error: {errorCode}
              </span>
            </div>
          )}

          <Button
            className="w-full h-11"
            onClick={() => router.push("/login")}
          >
            <RefreshCcw className="w-4 h-4 mr-2" />
            Try Again
          </Button>

          <Button
            variant="outline"
            className="w-full h-11"
            onClick={() => router.push("/")}
          >
            <Home className="w-4 h-4 mr-2" />
            Go Home
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense>
      <AuthErrorContent />
    </Suspense>
  );
}