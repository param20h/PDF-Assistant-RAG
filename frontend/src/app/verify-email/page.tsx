"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import { Brain } from "lucide-react";
import { api } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function VerifyEmailContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [message, setMessage] = useState(t("verifyEmail.checking"));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    api
      .get<{ message: string }>(`/api/v1/auth/verify?token=${encodeURIComponent(token)}`)
      .then((response) => {
        if (!cancelled) setMessage(response.message || t("verifyEmail.successFallback"));
      })
      .catch((err: unknown) => {
        const fallback = t("verifyEmail.errorFallback");
        if (!cancelled) setError(err instanceof Error ? err.message : fallback);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token, t]);

  const displayError = token ? error : t("verifyEmail.missingToken");
  const displayMessage = loading ? t("verifyEmail.checking") : displayError || message;

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-primary/8 rounded-full blur-[100px] pointer-events-none" />

      <Card className="w-full max-w-md relative z-10 bg-card/80 backdrop-blur-xl border-border/50 animate-fade-in-up">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-xl bg-primary/15 flex items-center justify-center">
              <Brain className="w-6 h-6 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">{t("verifyEmail.title")}</CardTitle>
          <CardDescription>{displayMessage}</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={
              displayError
                ? "p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive"
                : "p-3 rounded-lg bg-primary/10 border border-primary/30 text-sm text-primary"
            }
          >
            {displayMessage}
          </div>
          <Link href="/login" className={buttonVariants({ className: "w-full h-11 text-base mt-6" })}>
            {t("verifyEmail.signIn")}
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}
