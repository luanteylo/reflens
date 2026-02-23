"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Search, BookOpen } from "lucide-react";
import { useSearch, useFindReferences } from "@/hooks/use-search";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { EmptyState } from "@/components/shared/empty-state";
import type { PaperSummary } from "@/lib/types";

function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  return (
    <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
      {pct}% match
    </span>
  );
}

function PaperCard({ paper, score }: { paper: PaperSummary; score: number | null }) {
  return (
    <Link
      href={`/papers/${paper.id}`}
      className="block rounded-lg border border-border p-4 hover:bg-muted transition-colors"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium">{paper.title}</p>
        <ScoreBadge score={score} />
      </div>
      <p className="text-sm text-muted-foreground mt-1">
        {paper.authors.map((a) => a.name).join(", ")}
        {paper.year ? ` (${paper.year})` : ""}
      </p>
      {paper.abstract && (
        <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
          {paper.abstract}
        </p>
      )}
    </Link>
  );
}

export default function SearchPage() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [refText, setRefText] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setQuery(input), 300);
    return () => clearTimeout(timer);
  }, [input]);

  const { data, isLoading } = useSearch(query);
  const refMutation = useFindReferences();

  const handleFindRefs = () => {
    if (!refText.trim()) return;
    refMutation.mutate({ text: refText.trim(), limit: 10 });
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Search</h1>

      {/* Keyword / semantic search */}
      <section className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search papers..."
            className="w-full rounded-lg border border-border bg-background pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            autoFocus
          />
        </div>

        {isLoading && query && (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        )}

        {data && data.results.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {data.results.length} result{data.results.length !== 1 ? "s" : ""} for &quot;{data.query}&quot;
            </p>
            {data.results.map((item) => (
              <PaperCard key={item.paper.id} paper={item.paper} score={item.score} />
            ))}
          </div>
        )}

        {data && data.results.length === 0 && query && (
          <EmptyState message={`No results for "${query}"`} />
        )}

        {!query && (
          <p className="text-center py-4 text-muted-foreground">
            Type to search your paper library.
          </p>
        )}
      </section>

      {/* Reference finder */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Reference Finder</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Paste a sentence or claim, and we&apos;ll find papers that could support it.
        </p>
        <textarea
          value={refText}
          onChange={(e) => setRefText(e.target.value)}
          placeholder="e.g. Transformer-based models have significantly improved machine translation quality..."
          rows={3}
          className="w-full rounded-lg border border-border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
        />
        <button
          onClick={handleFindRefs}
          disabled={!refText.trim() || refMutation.isPending}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {refMutation.isPending ? "Searching..." : "Find References"}
        </button>

        {refMutation.isPending && (
          <div className="flex justify-center py-4">
            <LoadingSpinner />
          </div>
        )}

        {refMutation.data && refMutation.data.results.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {refMutation.data.results.length} reference{refMutation.data.results.length !== 1 ? "s" : ""} found
            </p>
            {refMutation.data.results.map((item) => (
              <div key={item.paper.id}>
                <PaperCard paper={item.paper} score={item.score} />
                {item.explanation && (
                  <p className="ml-4 mt-1 text-sm text-muted-foreground italic">
                    {item.explanation}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {refMutation.data && refMutation.data.results.length === 0 && (
          <EmptyState message="No matching references found" />
        )}
      </section>
    </div>
  );
}
