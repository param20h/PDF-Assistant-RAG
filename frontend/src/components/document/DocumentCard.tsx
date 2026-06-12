"use client";

import type { DocInfo } from "@/app/dashboard/page";
import KeywordTags from "./KeywordTags";

interface DocumentCardProps {
  document: DocInfo;
  isIndexing?: boolean;
}

export default function DocumentCard({ document, isIndexing }: DocumentCardProps) {
  const indexing =
    isIndexing ??
    (document.status === "processing" || document.status === "pending");

  return (
    <KeywordTags
      keywords={document.keywords}
      isIndexing={indexing}
    />
  );
}
