import { useState, useCallback } from "react";
import { PDFDocumentProxy } from "pdfjs-dist/types/src/display/api";

export interface SearchMatch {
  page: number;
  rects: { left: number; top: number; width: number; height: number }[];
}

interface TextItem {
  str: string;
  transform: number[];
}

export function usePdfSearch() {
  const [searchTerm, setSearchTerm] = useState("");
  const [matches, setMatches] = useState<SearchMatch[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  const performSearch = useCallback(
    async (pdfDoc: PDFDocumentProxy | null, term: string) => {
      if (!term || !pdfDoc) {
        setMatches([]);
        return;
      }

      const allMatches: SearchMatch[] = [];
      for (let i = 1; i <= pdfDoc.numPages; i++) {
        const page = await pdfDoc.getPage(i);
        const content = await page.getTextContent();

        // Simple match logic: In a production scenario, use a regex or PDF.js
        // built-in FindController for better accuracy.
        const textItems = content.items as TextItem[];
        textItems.forEach((item: TextItem) => {
          if (item.str.toLowerCase().includes(term.toLowerCase())) {
            allMatches.push({
              page: i,
              rects: [
                {
                  left: item.transform[4],
                  top: item.transform[5],
                  width: 50,
                  height: 10,
                },
              ],
            });
          }
        });
      }
      setMatches(allMatches);
      setCurrentIndex(0);
    },
    [],
  );

  return {
    searchTerm,
    setSearchTerm,
    matches,
    currentIndex,
    setCurrentIndex,
    performSearch,
  };
}
