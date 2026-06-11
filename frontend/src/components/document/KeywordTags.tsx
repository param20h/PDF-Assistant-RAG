// frontend/src/components/document/KeywordTags.tsx
"use client";

import { useState } from "react";

const PALETTE = [
  "bg-rose-100 text-rose-700",
  "bg-amber-100 text-amber-700",
  "bg-emerald-100 text-emerald-700",
  "bg-sky-100 text-sky-700",
  "bg-violet-100 text-violet-700",
  "bg-pink-100 text-pink-700",
  "bg-teal-100 text-teal-700",
];

function colorFor(word: string): string {
  let hash = 0;
  for (let i = 0; i < word.length; i++) {
    hash = (hash * 31 + word.charCodeAt(i)) & 0xffffffff;
  }
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

interface KeywordTagsProps {
  keywords?: string[];
  isIndexing?: boolean;
  maxVisible?: number;
}

export default function KeywordTags({
  keywords = [],
  isIndexing = false,
  maxVisible = 7,
}: KeywordTagsProps) {
  const [showAll, setShowAll] = useState(false);

  // Skeleton while indexing
  if (isIndexing) {
    return (
      <div className="flex flex-wrap gap-1 mt-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <span
            key={i}
            className="inline-block h-5 rounded-full bg-gray-200 animate-pulse"
            style={{ width: `${48 + (i % 3) * 16}px` }}
          />
        ))}
      </div>
    );
  }

  if (!keywords.length) return null;

  const visible = showAll ? keywords : keywords.slice(0, maxVisible);
  const overflow = keywords.length - maxVisible;

  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {visible.map((kw) => (
        <span
          key={kw}
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorFor(kw)}`}
        >
          {kw}
        </span>
      ))}
      {!showAll && overflow > 0 && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setShowAll(true);
          }}
          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
        >
          +{overflow} more
        </button>
      )}
    </div>
  );
}
