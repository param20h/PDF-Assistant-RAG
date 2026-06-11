"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type FontSize = "small" | "medium" | "large";

interface SettingsStore {
  fontSize: FontSize;
  setFontSize: (size: FontSize) => void;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      fontSize: "medium",
      setFontSize: (size) => set({ fontSize: size }),
    }),
    {
      name: "font-size-settings",
    }
  )
);
