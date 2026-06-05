"use client";

import { Toaster } from "sonner";

export function SonnerToaster() {
  return (
    <Toaster
      richColors
      closeButton
      position="top-right"
      toastOptions={{
        classNames: {
          toast: "rounded-xl border border-border/60 bg-popover/90 backdrop-blur supports-[backdrop-filter]:bg-popover/60",
          title: "font-semibold",
          description: "text-muted-foreground",
        },
      }}
    />
  );
}

