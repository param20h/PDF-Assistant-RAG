"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle, Folder } from "lucide-react";
import { getDriveFolders, type DriveFolder } from "@/services/drive-api";
import { Button } from "@/components/ui/button";

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

  useEffect(() => {
    let active = true;

    void getDriveFolders().then((data) => {
      if (!active) return;
      setFolders(data);
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, []);

  const selectedFolder = useMemo(
    () => folders.flatMap((folder) => collectFolders(folder)).find((folder) => folder.id === selectedId) ?? null,
    [folders, selectedId]
  );

  const handleToggle = (id: string) => {
    setExpandedIds((current) => ({
      ...current,
      [id]: !current[id],
    }));
  };

  const handleSelect = (folder: DriveFolder) => {
    setSelectedId(folder.id);
    onSelect?.(folder);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-border/70 bg-card/80 p-4 shadow-sm backdrop-blur-xl">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Google Drive</p>
            <h2 className="text-xl font-semibold">Select a folder</h2>
          </div>
          <div className="text-sm text-muted-foreground">
            Pick exactly one folder from the tree.
          </div>
        </div>

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-11 rounded-lg bg-muted/50 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-1">
            {folders.map((folder) => (
              <FolderItem
                key={folder.id}
                folder={folder}
                depth={0}
                expandedIds={expandedIds}
                onToggle={handleToggle}
                selectedId={selectedId}
                onSelect={handleSelect}
              />
            ))}
          </div>
        )}
      </div>

      <div className="rounded-3xl border border-border/70 bg-card/80 p-4 text-sm text-muted-foreground">
        <div className="mb-3 flex items-center justify-between gap-3">
          <span className="font-semibold text-foreground">Selected folder</span>
          <span className="rounded-full bg-muted px-3 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">
            {selectedFolder ? "Ready" : "None"}
          </span>
        </div>

        {selectedFolder ? (
          <div className="space-y-1 rounded-2xl border border-border/50 bg-background/80 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Folder className="h-4 w-4 text-primary" />
              <span>{selectedFolder.name}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Folder ID: {selectedFolder.id}
            </p>
          </div>
        ) : (
          <p>Please select a folder to continue.</p>
        )}
      </div>

      <div className="flex justify-end">
        <Button
          type="button"
          variant="secondary"
          onClick={() => void (selectedFolder && window.alert(`Selected folder: ${selectedFolder.name}`))}
          disabled={!selectedFolder}
        >
          Confirm selection
        </Button>
      </div>
    </div>
  );
}

function collectFolders(folder: DriveFolder): DriveFolder[] {
  return [folder, ...(folder.children ?? []).flatMap(collectFolders)];
}
