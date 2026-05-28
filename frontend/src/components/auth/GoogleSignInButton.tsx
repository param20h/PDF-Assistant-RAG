"use client";

import { useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleAccountsId = {
  initialize: (options: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void | Promise<void>;
  }) => void;
  renderButton: (element: HTMLElement, options: Record<string, string | number | boolean>) => void;
};

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: GoogleAccountsId;
      };
    };
  }
}

type GoogleSignInButtonProps = {
  onError: (message: string) => void;
  onSuccess: () => void;
};

const GOOGLE_SCRIPT_ID = "google-identity-services";
const GOOGLE_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

export default function GoogleSignInButton({ onError, onSuccess }: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const { loginWithGoogle } = useAuth();
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || !buttonRef.current) return;

    let cancelled = false;

    const renderButton = () => {
      if (cancelled || !buttonRef.current || !window.google?.accounts?.id) return;

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          if (!response.credential) {
            onError("Google did not return a sign-in credential");
            return;
          }

          try {
            await loginWithGoogle(response.credential);
            onSuccess();
          } catch (error) {
            onError(error instanceof Error ? error.message : "Google sign-in failed");
          }
        },
      });

      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        width: 360,
      });
    };

    const existingScript = document.getElementById(GOOGLE_SCRIPT_ID) as HTMLScriptElement | null;
    if (existingScript) {
      if (window.google?.accounts?.id) renderButton();
      existingScript.addEventListener("load", renderButton, { once: true });
      return () => {
        cancelled = true;
        existingScript.removeEventListener("load", renderButton);
      };
    }

    const script = document.createElement("script");
    script.id = GOOGLE_SCRIPT_ID;
    script.src = GOOGLE_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = renderButton;
    script.onerror = () => onError("Google sign-in could not be loaded");
    document.head.appendChild(script);

    return () => {
      cancelled = true;
      script.onload = null;
      script.onerror = null;
    };
  }, [clientId, loginWithGoogle, onError, onSuccess]);

  if (!clientId) return null;

  return <div className="flex justify-center" ref={buttonRef} />;
}
