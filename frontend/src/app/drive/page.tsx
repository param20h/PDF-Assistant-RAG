"use client";

import DriveFolderSelector from "@/components/DriveFolderSelector";

export default function DrivePage() {
  return (
    <main className="min-h-screen bg-background px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <section className="rounded-3xl border border-border/70 bg-card/80 p-6 shadow-sm backdrop-blur-xl">
          <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Drive connector demo</p>
              <h1 className="text-3xl font-semibold">Google Drive Folder Selector</h1>
            </div>
            <p className="max-w-xl text-sm leading-6 text-muted-foreground">
              Browse a mocked Google Drive folder tree, expand nested folders, and select one target folder to integrate with uploads or document imports.
            </p>
          </div>
        </section>

        <DriveFolderSelector />
      </div>
    </main>
  );
}
