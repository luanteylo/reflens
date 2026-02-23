"use client";

import { useState } from "react";
import Link from "next/link";
import { User } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { EmptyState } from "@/components/shared/empty-state";
import { Pagination } from "@/components/shared/pagination";

const PAGE_SIZE = 50;

export default function AuthorsPage() {
  const [offset, setOffset] = useState(0);
  const [selectedAuthor, setSelectedAuthor] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["authors", offset],
    queryFn: () => api.authors.list(PAGE_SIZE, offset),
  });

  const { data: authorPapers, isLoading: loadingPapers } = useQuery({
    queryKey: ["author-papers", selectedAuthor],
    queryFn: () => api.authors.papers(selectedAuthor!),
    enabled: !!selectedAuthor,
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
      <h1 className="text-2xl font-bold">Authors</h1>

      {!data || data.authors.length === 0 ? (
        <EmptyState message="No authors yet. Upload papers to see authors here." />
      ) : (
        <>
          <div className="grid grid-cols-[300px_1fr] gap-6">
            <div className="space-y-1">
              {data.authors.map((author) => (
                <button
                  key={author.id}
                  onClick={() => setSelectedAuthor(author.id)}
                  className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-left transition-colors ${
                    selectedAuthor === author.id
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted text-muted-foreground"
                  }`}
                >
                  <User className="h-4 w-4 shrink-0" />
                  <span className="truncate">{author.name}</span>
                </button>
              ))}
            </div>

            <div>
              {selectedAuthor && loadingPapers && (
                <div className="flex justify-center py-8">
                  <LoadingSpinner />
                </div>
              )}
              {authorPapers && authorPapers.length > 0 && (
                <div className="space-y-3">
                  <h2 className="text-lg font-semibold">
                    Papers by {data.authors.find((a) => a.id === selectedAuthor)?.name}
                  </h2>
                  {authorPapers.map((paper) => (
                    <Link
                      key={paper.id}
                      href={`/papers/${paper.id}`}
                      className="block rounded-lg border border-border p-4 hover:bg-muted transition-colors"
                    >
                      <p className="font-medium">{paper.title}</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {paper.authors.map((a) => a.name).join(", ")}
                        {paper.year ? ` (${paper.year})` : ""}
                      </p>
                    </Link>
                  ))}
                </div>
              )}
              {authorPapers && authorPapers.length === 0 && (
                <p className="text-muted-foreground">No papers found for this author.</p>
              )}
              {!selectedAuthor && (
                <p className="py-8 text-center text-muted-foreground">
                  Select an author to see their papers.
                </p>
              )}
            </div>
          </div>

          <Pagination
            total={data.total}
            limit={data.limit}
            offset={offset}
            onPageChange={setOffset}
          />
        </>
      )}
    </div>
  );
}
