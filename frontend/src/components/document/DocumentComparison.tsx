"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import type { DocInfo } from "@/app/dashboard/page";
import { Columns, X, ArrowLeftRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const PDFViewer = dynamic(() => import("./PDFViewer"), {
  ssr: false,
  loading: () => <div className="h-full bg-muted animate-pulse rounded-xl" />,
});

interface Props {
  documents: DocInfo[];
  onClose: () => void;
}

export default function DocumentComparison({ documents, onClose }: Props) {
  const [doc1Id, setDoc1Id] = useState<string | null>(documents.length >= 2 ? documents[0].id : null);
  const [doc2Id, setDoc2Id] = useState<string | null>(documents.length >= 2 ? documents[1].id : null);
  const [page1, setPage1] = useState(1);
  const [page2, setPage2] = useState(1);

  const doc1 = documents.find(d => d.id === doc1Id) || (documents.length > 0 ? documents[0] : null);
  const doc2 = documents.find(d => d.id === doc2Id) || (documents.length > 1 ? documents[1] : null);

  if (documents.length < 2) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-4">
        <div className="p-4 bg-muted rounded-full">
          <Columns size={48} className="text-muted-foreground" />
        </div>
        <h2 className="text-xl font-bold">Comparison Unavailable</h2>
        <p className="text-muted-foreground max-w-xs text-sm">
          You need at least two uploaded documents to use the comparison view.
        </p>
        <Button onClick={onClose}>Back to Dashboard</Button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden animate-in fade-in zoom-in-95 duration-300">
      <div className="h-14 border-b border-border/50 flex items-center justify-between px-6 bg-card/30 backdrop-blur-md shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 text-primary rounded-lg">
            <ArrowLeftRight size={18} />
          </div>
          <h2 className="font-bold text-sm uppercase tracking-wider">Document Comparison</h2>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X size={20} />
        </Button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Side */}
        <div className="flex-1 flex flex-col border-r border-border/50 overflow-hidden">
          <div className="p-3 bg-muted/30 border-b border-border/50 shrink-0">
            <select
              className="w-full bg-transparent text-sm font-bold focus:outline-none cursor-pointer"
              value={doc1?.id || ""}
              onChange={(e) => setDoc1Id(e.target.value)}
            >
              {documents.map(d => (
                <option key={d.id} value={d.id}>{d.original_name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 overflow-hidden">
            {doc1 && (
              <PDFViewer
                documentId={doc1.id}
                currentPage={page1}
                onPageChange={setPage1}
                totalPages={doc1.page_count}
              />
            )}
          </div>
        </div>

        {/* Right Side */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="p-3 bg-muted/30 border-b border-border/50 shrink-0">
            <select
              className="w-full bg-transparent text-sm font-bold focus:outline-none cursor-pointer"
              value={doc2?.id || ""}
              onChange={(e) => setDoc2Id(e.target.value)}
            >
              {documents.map(d => (
                <option key={d.id} value={d.id}>{d.original_name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 overflow-hidden">
            {doc2 && (
              <PDFViewer
                documentId={doc2.id}
                currentPage={page2}
                onPageChange={setPage2}
                totalPages={doc2.page_count}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
