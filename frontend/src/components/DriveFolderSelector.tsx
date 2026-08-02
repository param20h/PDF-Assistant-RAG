"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle, Folder } from "lucide-react";
import { getDriveFolders, type DriveFolder } from "@/services/drive-api";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface DriveFolderSelectorProps {
  onSelect?: (folder: DriveFolder) => void;
}

function FolderItem({
  folder,
  depth,
  expandedIds,
  onToggle,
  selectedId,
  onSelect,
}: {
  folder: DriveFolder;
  depth: number;
  expandedIds: Record<string, boolean>;
  onToggle: (id: string) => void;
  selectedId: string | null;
  onSelect: (folder: DriveFolder) => void;
}) {
  const hasChildren = Array.isArray(folder.children) && folder.children.length > 0;
  const isExpanded = expandedIds[folder.id] === true;
  const isSelected = folder.id === selectedId;

  return (
    <div>
      <div
        className={`flex items-center gap-2 rounded-xl px-3 py-2 transition-colors ${
          isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
        }`}
        style={{ paddingLeft: `${depth * 1.5}rem` }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted/70"
            onClick={() => onToggle(folder.id)}
            aria-label={isExpanded ? "Collapse folder" : "Expand folder"}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <div className="h-8 w-8 flex items-center justify-center text-muted-foreground">
            <span className="h-4 w-4" />
          </div>
        )}

        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-sm font-medium leading-tight text-foreground"
          onClick={() => onSelect(folder)}
        >
          <Folder className="h-4 w-4 text-primary" />
          <span className="truncate">{folder.name}</span>
        </button>

        {isSelected && <CheckCircle className="h-4 w-4 text-emerald-500" />}
      </div>

      {hasChildren && isExpanded && (
        <div className="border-l border-border/50">
          {folder.children?.map((child) => (
            <FolderItem
              key={child.id}
              folder={child}
              depth={depth + 1}
              expandedIds={expandedIds}
              onToggle={onToggle}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DriveFolderSelector({ onSelect }: DriveFolderSelectorProps) {
  const [folders, setFolders] = useState<DriveFolder[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [syncProgress, setSyncProgress] = useState(0);
  const [folderPath, setFolderPath] = useState<DriveFolder[]>([]);

  useEffect(() => {
    let active = true;

    const interval = setInterval(() => {
      setSyncProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 150);

    void getDriveFolders().then((data) => {
    .catch(err => console.error(err))