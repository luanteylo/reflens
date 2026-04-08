"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Search, Loader2, ChevronDown, FolderOpen, Bookmark, X, Clock, Copy, Check } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useFindReferences } from "@/hooks/use-search";
import type { ReferenceResult, PaperGroup, SavedSearch } from "@/lib/types";

function StanceBadge({ stance }: { stance: ReferenceResult["stance"] }) {
  if (!stance) return null;
  const styles = {
    supports: "text-green-700",
    contradicts: "text-red-700",
    neutral: "text-gray-500",
  };
  return (
    <span className={`text-xs font-medium ${styles[stance]}`}>
      {stance}
    </span>
  );
}

function CopyBibtexButton({ paperId }: { paperId: string }) {
  const [state, setState] = useState<"idle" | "loading" | "copied">("idle");

  const handleCopy = async () => {
    setState("loading");
    try {
      const bibtex = await api.papers.bibtex(paperId);
      await navigator.clipboard.writeText(bibtex);
      setState("copied");
      setTimeout(() => setState("idle"), 2000);
    } catch {
      setState("idle");
    }
  };

  return (
    <button
      onClick={handleCopy}
      disabled={state === "loading"}
      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      title="Copy BibTeX"
    >
      {state === "copied" ? (
        <>
          <Check className="h-3 w-3 text-green-600" />
          <span className="text-green-600">Copied</span>
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          BibTeX
        </>
      )}
    </button>
  );
}

function ResultCard({ item }: { item: ReferenceResult }) {
  const { paper } = item;
  const authors = paper.authors.map((a) => a.name).join(", ");
  const pct = item.score != null ? Math.round(item.score * 100) : null;

  return (
    <div className="max-w-2xl py-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {authors}
        {paper.year ? ` · ${paper.year}` : ""}
        {pct != null && <span className="text-primary">{pct}% match</span>}
        <StanceBadge stance={item.stance} />
        <span className="text-border">|</span>
        <CopyBibtexButton paperId={paper.id} />
      </div>
      <h3 className="text-lg text-primary mt-0.5 leading-snug">
        {paper.title}
      </h3>
      {item.explanation && (
        <p className="text-sm text-foreground/70 mt-1 leading-relaxed">
          {item.explanation}
        </p>
      )}
      {paper.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {paper.tags.map((t) => (
            <span
              key={t.id}
              className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground"
            >
              {t.tag_name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function GroupSelector({
  groups,
  selected,
  onSelect,
}: {
  groups: PaperGroup[];
  selected: PaperGroup | null;
  onSelect: (group: PaperGroup | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (groups.length === 0) return null;

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
      >
        <FolderOpen className="h-3.5 w-3.5" />
        {selected ? selected.name : "All papers"}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 min-w-[180px] rounded-lg border border-border bg-white shadow-lg overflow-hidden">
          <button
            onClick={() => { onSelect(null); setOpen(false); }}
            className={`flex w-full items-center px-3 py-2 text-sm text-left hover:bg-muted transition-colors ${
              !selected ? "font-medium text-foreground" : "text-muted-foreground"
            }`}
          >
            All papers
          </button>
          {groups.map((g) => (
            <button
              key={g.id}
              onClick={() => { onSelect(g); setOpen(false); }}
              className={`flex w-full items-center justify-between px-3 py-2 text-sm text-left hover:bg-muted transition-colors ${
                selected?.id === g.id ? "font-medium text-foreground" : "text-muted-foreground"
              }`}
            >
              <span>{g.name}</span>
              <span className="text-xs opacity-60">{g.paper_count}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SavedSearchItem({
  search,
  onLoad,
  onDelete,
}: {
  search: SavedSearch;
  onLoad: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="group flex items-center gap-2">
      <button
        onClick={onLoad}
        className="flex-1 text-left text-sm text-muted-foreground hover:text-foreground transition-colors truncate"
        title={search.text}
      >
        <span className="line-clamp-1">{search.text}</span>
      </button>
      {search.group_name && (
        <span className="text-xs text-muted-foreground/60 shrink-0">
          {search.group_name}
        </span>
      )}
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-all shrink-0"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

export default function HomePage() {
  const [input, setInput] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<PaperGroup | null>(null);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [cachedResults, setCachedResults] = useState<ReferenceResult[] | null>(null);
  const refMutation = useFindReferences();
  const qc = useQueryClient();

  const { data: groupsData } = useQuery({
    queryKey: ["groups"],
    queryFn: () => api.groups.list(),
  });

  const { data: savedSearchesData } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => api.savedSearches.list(),
  });

  const saveMutation = useMutation({
    mutationFn: ({ text, groupId, results }: { text: string; groupId?: string; results?: ReferenceResult[] }) =>
      api.savedSearches.save(text, groupId, results),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saved-searches"] });
      setSaved(true);
    },
    onError: () => {
      setSaveError(true);
      setTimeout(() => setSaveError(false), 2500);
    },
  });

  const deleteSavedMutation = useMutation({
    mutationFn: (id: string) => api.savedSearches.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-searches"] }),
  });

  const groups = groupsData?.groups ?? [];
  const savedSearches = savedSearchesData?.searches ?? [];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    setHasSearched(true);
    setSaved(false);
    setCachedResults(null);
    refMutation.mutate({
      text: input.trim(),
      limit: 10,
      explain: true,
      group_id: selectedGroup?.id,
    });
  };

  const loadSavedSearch = (search: SavedSearch) => {
    setInput(search.text);
    const group = search.group_id
      ? groups.find((g) => g.id === search.group_id) ?? null
      : null;
    setSelectedGroup(group);
    setHasSearched(true);
    setSaved(true);
    if (search.results && search.results.length > 0) {
      setCachedResults(search.results);
    } else {
      setCachedResults(null);
      refMutation.mutate({
        text: search.text,
        limit: 10,
        explain: true,
        group_id: search.group_id ?? undefined,
      });
    }
  };

  // Results: prefer cached, fallback to live mutation
  const displayResults = cachedResults ?? refMutation.data?.results ?? null;
  const isSearching = !cachedResults && refMutation.isPending;

  // Landing state: centered logo + search
  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4">
        <h1 className="text-5xl font-light tracking-tight text-foreground mb-8">
          Ref<span className="text-primary font-normal">Lens</span>
        </h1>
        <form onSubmit={handleSearch} className="w-full max-w-xl space-y-3">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Paste a claim to find supporting (or contradicting) references..."
              className="w-full rounded-full border border-border bg-white px-12 py-3.5 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              autoFocus
            />
          </div>
          <div className="flex items-center justify-center gap-3">
            <GroupSelector
              groups={groups}
              selected={selectedGroup}
              onSelect={setSelectedGroup}
            />
            <p className="text-xs text-muted-foreground">
              {selectedGroup
                ? `Searching in "${selectedGroup.name}"`
                : "Searching all papers"}
            </p>
          </div>
        </form>

        {/* Saved searches */}
        {savedSearches.length > 0 && (
          <div className="mt-10 w-full max-w-md space-y-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground/60">
              <Clock className="h-3 w-3" />
              Saved searches
            </div>
            <div className="space-y-1.5">
              {savedSearches.map((s) => (
                <SavedSearchItem
                  key={s.id}
                  search={s}
                  onLoad={() => loadSavedSearch(s)}
                  onDelete={() => deleteSavedMutation.mutate(s.id)}
                />
              ))}
            </div>
          </div>
        )}

        <Link
          href="/library"
          className="mt-10 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Manage your paper library
        </Link>
      </div>
    );
  }

  // Results state: search bar on top, results below
  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <div className="border-b border-border bg-white sticky top-0 z-10">
        <div className="flex items-center gap-4 px-6 py-3 max-w-4xl">
          <Link
            href="/"
            onClick={(e) => {
              e.preventDefault();
              setHasSearched(false);
              setInput("");
              setSaved(false);
            }}
            className="text-xl font-light tracking-tight text-foreground shrink-0"
          >
            Ref<span className="text-primary font-normal">Lens</span>
          </Link>
          <form onSubmit={handleSearch} className="flex-1 max-w-xl">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={input}
                onChange={(e) => { setInput(e.target.value); setSaved(false); setCachedResults(null); }}
                className="w-full rounded-full border border-border bg-white pl-10 pr-4 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                autoFocus
              />
            </div>
          </form>
          <GroupSelector
            groups={groups}
            selected={selectedGroup}
            onSelect={setSelectedGroup}
          />
          <Link
            href="/library"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            Library
          </Link>
        </div>
      </div>

      {/* Results */}
      <div className="px-6 py-4 max-w-4xl">
        {isSearching && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
            <Loader2 className="h-4 w-4 animate-spin" />
            Finding references...
          </div>
        )}

        {displayResults && displayResults.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-muted-foreground">
                {displayResults.length} reference{displayResults.length !== 1 ? "s" : ""} found
                {selectedGroup ? ` in "${selectedGroup.name}"` : ""}
              </p>
              <button
                onClick={() => saveMutation.mutate({ text: input.trim(), groupId: selectedGroup?.id, results: displayResults })}
                disabled={saved || saveMutation.isPending}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  saved
                    ? "text-primary"
                    : saveError
                      ? "border border-destructive text-destructive"
                      : "border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                <Bookmark className={`h-3 w-3 ${saved ? "fill-primary" : ""}`} />
                {saveMutation.isPending ? "Saving..." : saved ? "Saved" : saveError ? "Failed to save" : "Save search"}
              </button>
            </div>
            <div className="divide-y divide-border">
              {displayResults.map((item) => (
                <ResultCard key={item.paper.id} item={item} />
              ))}
            </div>
          </div>
        )}

        {displayResults && displayResults.length === 0 && (
          <p className="text-sm text-muted-foreground py-8">
            No matching references found. Try rephrasing your claim
            {selectedGroup ? " or searching all papers." : "."}
          </p>
        )}

        {refMutation.error && !cachedResults && (
          <p className="text-sm text-destructive py-8">
            Something went wrong. Please try again.
          </p>
        )}
      </div>
    </div>
  );
}
