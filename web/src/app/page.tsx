"use client";

import Link from "next/link";
import { FileText, Search, Upload } from "lucide-react";
import { usePapers } from "@/hooks/use-papers";
import { LoadingSpinner } from "@/components/shared/loading-spinner";

export default function DashboardPage() {
  const { data, isLoading } = usePapers(5, 0);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-border bg-card p-6">
          <div className="flex items-center gap-3">
            <FileText className="h-8 w-8 text-primary" />
            <div>
              <p className="text-2xl font-bold">{isLoading ? "--" : data?.total ?? 0}</p>
              <p className="text-sm text-muted-foreground">Total Papers</p>
            </div>
          </div>
        </div>
        <Link
          href="/upload"
          className="rounded-lg border border-border bg-card p-6 hover:bg-muted transition-colors"
        >
          <div className="flex items-center gap-3">
            <Upload className="h-8 w-8 text-primary" />
            <div>
              <p className="text-lg font-semibold">Upload Paper</p>
              <p className="text-sm text-muted-foreground">Add a new PDF</p>
            </div>
          </div>
        </Link>
        <Link
          href="/search"
          className="rounded-lg border border-border bg-card p-6 hover:bg-muted transition-colors"
        >
          <div className="flex items-center gap-3">
            <Search className="h-8 w-8 text-primary" />
            <div>
              <p className="text-lg font-semibold">Search</p>
              <p className="text-sm text-muted-foreground">Find papers by title</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Recent papers */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Papers</h2>
          <Link href="/papers" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="space-y-2">
            {data?.papers.map((paper) => (
              <Link
                key={paper.id}
                href={`/papers/${paper.id}`}
                className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-muted transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">{paper.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {paper.authors.map((a) => a.name).join(", ")}
                    {paper.year ? ` (${paper.year})` : ""}
                  </p>
                </div>
                {paper.ai_summary && (
                  <span className="ml-3 rounded-full bg-accent px-2 py-0.5 text-xs text-accent-foreground">
                    Summarized
                  </span>
                )}
              </Link>
            ))}
            {data?.papers.length === 0 && (
              <p className="text-center py-8 text-muted-foreground">
                No papers yet. <Link href="/upload" className="text-primary hover:underline">Upload one</Link> to get started.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
