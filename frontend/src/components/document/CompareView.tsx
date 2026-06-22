"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { X, Columns2, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { DocInfo } from "@/app/dashboard/page";

function PDFViewerSkeleton() {
  return (
    <div className="h-full flex flex-col bg-background animate-pulse">
      <div className="h-10 border-b border-border/50 bg-card/50" />
      <div className="flex-1 bg-muted/40" />
    </div>
  );
}

const PDFViewer = dynamic(() => import("@/components/document/PDFViewer"), {
  ssr: false,
  loading: () => <PDFViewerSkeleton />,
});

interface Props {
  documents: DocInfo[];
  onClose: () => void;
}

export default function CompareView({ documents, onClose }: Props) {
  const pdfDocs = documents.filter(
    (d) => d.status === "ready" && d.original_name.endsWith(".pdf"),
  );

  const [leftDoc, setLeftDoc] = useState<DocInfo | null>(pdfDocs[0] ?? null);
  const [rightDoc, setRightDoc] = useState<DocInfo | null>(pdfDocs[1] ?? null);
  const [leftPage, setLeftPage] = useState(1);
  const [rightPage, setRightPage] = useState(1);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50 bg-card/50 shrink-0">
        <Columns2 className="w-4 h-4 text-muted-foreground shrink-0" />
        <span className="text-sm font-medium">Compare Documents</span>

        <div className="flex items-center gap-2 ml-4">
          <DocPicker
            label="Left"
            selected={leftDoc}
            options={pdfDocs}
            exclude={rightDoc}
            onSelect={(doc) => {
              setLeftDoc(doc);
              setLeftPage(1);
            }}
          />

          <span className="text-muted-foreground text-xs shrink-0">vs</span>

          <DocPicker
            label="Right"
            selected={rightDoc}
            options={pdfDocs}
            exclude={leftDoc}
            onSelect={(doc) => {
              setRightDoc(doc);
              setRightPage(1);
            }}
          />
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 ml-auto"
          onClick={onClose}
          aria-label="Close compare view"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* ── Split Panes ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left pane */}
        <div className="flex-1 min-w-0 border-r border-border/50 overflow-hidden">
          {leftDoc ? (
            <PDFViewer
              documentId={leftDoc.id}
              currentPage={leftPage}
              onPageChange={setLeftPage}
              totalPages={leftDoc.page_count}
              highlightTarget={null}
            />
          ) : (
            <EmptyPane side="left" />
          )}
        </div>

        {/* Right pane */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {rightDoc ? (
            <PDFViewer
              documentId={rightDoc.id}
              currentPage={rightPage}
              onPageChange={setRightPage}
              totalPages={rightDoc.page_count}
              highlightTarget={null}
            />
          ) : (
            <EmptyPane side="right" />
          )}
        </div>
      </div>
    </div>
  );
}

function DocPicker({
  label,
  selected,
  options,
  exclude,
  onSelect,
}: {
  label: string;
  selected: DocInfo | null;
  options: DocInfo[];
  exclude: DocInfo | null;
  onSelect: (doc: DocInfo) => void;
}) {
  const available = options.filter((d) => d.id !== exclude?.id);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="outline"
            size="sm"
            className="h-7 max-w-[180px] text-xs gap-1"
          />
        }
      >
        <span className="text-muted-foreground shrink-0">{label}:</span>
        <span className="truncate">
          {selected?.original_name ?? "Select PDF"}
        </span>
        <ChevronDown className="w-3 h-3 shrink-0" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-w-[260px]">
        {available.length === 0 ? (
          <DropdownMenuItem disabled>No other PDFs available</DropdownMenuItem>
        ) : (
          available.map((doc) => (
            <DropdownMenuItem
              key={doc.id}
              onClick={() => onSelect(doc)}
              className="text-xs truncate"
            >
              {doc.original_name}
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function EmptyPane({ side }: { side: "left" | "right" }) {
  return (
    <div className="h-full flex items-center justify-center text-center p-6">
      <div>
        <Columns2 className="w-8 h-8 mx-auto text-muted-foreground/30 mb-3" />
        <p className="text-sm text-muted-foreground">
          Select a PDF for the {side} pane
        </p>
        <p className="text-xs text-muted-foreground/60 mt-1">
          Use the dropdown above to choose a document
        </p>
      </div>
    </div>
  );
}
