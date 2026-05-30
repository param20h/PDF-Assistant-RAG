import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { TooltipProvider } from "@/components/ui/tooltip";
import I18nProvider from "@/components/providers/I18nProvider";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { Github, Twitter, MessageSquare } from "lucide-react";


const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Document AI Analyst — Enterprise RAG System",
  description:
    "Upload complex PDFs and chat with an AI agent that pulls specific insights, summarizes data, and accurately cites sources using Retrieval-Augmented Generation.",
  keywords: ["RAG", "Document AI", "PDF Analysis", "LLM", "Vector Search"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
                        <AuthProvider>
            <I18nProvider>
              <TooltipProvider>{children}</TooltipProvider>
            </I18nProvider>
          </AuthProvider>
        </ThemeProvider>

        <footer className="w-full border-t border-border py-4 bg-background z-50">
          <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground">
              &copy; {new Date().getFullYear()} PDF-Assistant-RAG. All rights reserved.
            </p>
            
            <div className="flex items-center gap-4">
              <a 
                href="https://github.com" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors duration-200"
                aria-label="GitHub Repository"
              >
                <Github className="h-4 w-4" />
              </a>

              <a 
                href="https://x.com" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors duration-200"
                aria-label="Twitter X Profile"
              >
                <Twitter className="h-4 w-4" />
              </a>

              <a 
                href="https://discord.gg" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors duration-200"
                aria-label="Discord Server"
              >
                <MessageSquare className="h-4 w-4" /> 
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

