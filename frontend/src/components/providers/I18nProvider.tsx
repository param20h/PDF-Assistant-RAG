"use client";

import { useEffect } from "react";
import { I18nextProvider } from "react-i18next";
import i18n from "@/lib/i18n";

export default function I18nProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage || "en";

    const handleLanguageChanged = (language: string) => {
      document.documentElement.lang = language;
    };

    i18n.on("languageChanged", handleLanguageChanged);
    return () => {
      i18n.off("languageChanged", handleLanguageChanged);
    };
  }, []);

  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
