"use client"

import * as React from "react"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

const variantStyles = {
  danger: {
    confirmVariant: "destructive" as const,
    icon: "text-destructive",
    border: "data-closed:animate-out",
  },
  warning: {
    confirmVariant: "secondary" as const,
    icon: "text-amber-500",
    border: "data-closed:animate-out",
  },
  default: {
    confirmVariant: "default" as const,
    icon: "text-primary",
    border: "data-closed:animate-out",
  },
} as const

export interface ConfirmationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  message: string | React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  variant?: "default" | "danger" | "warning"
  loading?: boolean
  onConfirm: () => void | Promise<void>
}

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  loading = false,
  onConfirm,
}: ConfirmationDialogProps) {
  const style = variantStyles[variant]

  const handleConfirm = async () => {
    await onConfirm()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          "sm:max-w-md",
          variant === "danger" && "sm:border-destructive/20",
          variant === "warning" && "sm:border-amber-500/20",
        )}
        showCloseButton={!loading}
      >
        <DialogHeader>
          <DialogTitle
            className={cn(
              variant === "danger" && "text-destructive",
              variant === "warning" && "text-amber-600 dark:text-amber-400",
            )}
          >
            {title}
          </DialogTitle>
          <DialogDescription asChild={typeof message !== "string"}>
            {typeof message === "string" ? (
              <span className="text-sm text-muted-foreground">{message}</span>
            ) : (
              message
            )}
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={style.confirmVariant}
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading && <Loader2 className="mr-1.5 size-4 animate-spin" />}
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
