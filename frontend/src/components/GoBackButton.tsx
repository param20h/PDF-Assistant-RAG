"use client";

import { Button } from "@/components/ui/button";

export function GoBackButton() {
  return (
    <Button variant="outline" onClick={() => window.history.back()}>
      Go Back
    </Button>
  );
}