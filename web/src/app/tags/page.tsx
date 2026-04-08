"use client";

import { useState } from "react";
import Link from "next/link";
import { Tags } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { EmptyState } from "@/components/shared/empty-state";
import type { Tag, PaperSummary } from "@/lib/types";

export default function TagsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.tags.list(),
  });
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  const { data: tagPapers, isLoading: loadingPapers } = useQuery({
    queryKey: ["tag-papers", selectedTag],
    queryFn: () => api.tags.papers(selectedTag!),
    enabled: !!selectedTag,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tags</h1>

      {!data || data.tags.length === 0 ? (
        <EmptyState message="No tags yet. Generate tags for your papers to see them here." />
      ) : (
        <div className="grid grid-cols-[300px_1fr] gap-6">
          <div className="space-y-1">
            {data.tags.map((tag) => (
              <button
                key={tag.id}
                onClick={() => setSelectedTag(tag.id)}
                className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-left transition-colors ${
                  selectedTag === tag.id
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-muted text-muted-foreground"
                }`}
              >
                <Tags className="h-4 w-4 shrink-0" />
                {tag.name}
              </button>
            ))}
          </div>

          <div>
            {selectedTag && loadingPapers && (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            )}
            {tagPapers && (
              <div className="space-y-3">
                <h2 className="text-lg font-semibold">{tagPapers.tag.name}</h2>
                {tagPapers.papers.length > 0 ? (
                  tagPapers.papers.map((paper) => (
                    <Link
                      key={paper.id}
                      href={`/papers/${paper.id}`}
                      className="block rounded-lg border border-border p-4 hover:bg-muted transition-colors"
                    >
                      <p className="font-medium truncate">{paper.title}</p>
                      <p className="text-sm text-muted-foreground mt-1 truncate">
                        {paper.authors.map((a: { name: string }) => a.name).join(", ")}
                        {paper.year ? ` (${paper.year})` : ""}
                      </p>
                    </Link>
                  ))
                ) : (
                  <p className="text-muted-foreground">No papers with this tag.</p>
                )}
              </div>
            )}
            {!selectedTag && (
              <p className="py-8 text-center text-muted-foreground">
                Select a tag to see its papers.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
