"use client";

import { create } from "zustand";

export type WorkspaceId = "personal" | "company";

interface WorkspaceStore {
  workspace: WorkspaceId;
  setWorkspace: (id: WorkspaceId) => void;
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  workspace: "personal",
  setWorkspace(id: WorkspaceId) {
    set({ workspace: id });
  },
}));

export const WORKSPACES: { id: WorkspaceId; label: string }[] = [
  { id: "personal", label: "Personal" },
  { id: "company", label: "Company" },
];
