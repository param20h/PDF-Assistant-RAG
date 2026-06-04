import { useEffect, RefObject } from "react";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

export function useFocusTrap(ref: RefObject<HTMLElement>, active: boolean) {
  useEffect(() => {
    if (!active || !ref.current) return;

    const el = ref.current;
    const focusable = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE));
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    // Focus the first focusable element when drawer opens
    first?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Tab") return;
      if (focusable.length === 0) { e.preventDefault(); return; }

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }

    el.addEventListener("keydown", handleKeyDown);
    return () => el.removeEventListener("keydown", handleKeyDown);
  }, [active, ref]);
}
