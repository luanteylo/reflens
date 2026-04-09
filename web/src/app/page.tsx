"use client";

import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import Link from "next/link";
import { Search, Loader2, ChevronDown, FolderOpen, Bookmark, X, Clock, Copy, Check, Sparkles, FileText, Maximize2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, getPdfUrl } from "@/lib/api";
import { useSearch } from "@/hooks/use-search";
import type { ReferenceResult, SearchResultItem, PaperCollection, SavedSearch } from "@/lib/types";

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

const CitePanel = forwardRef<{ toggle: () => void }, { paperId: string }>(function CitePanel({ paperId }, ref) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<{ short: string; full: string; bibtex: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleToggle = async () => {
    if (open) { setOpen(false); return; }
    setOpen(true);
    if (!data) {
      setLoading(true);
      try {
        const result = await api.papers.cite(paperId);
        setData(result);
      } catch { /* ignore */ }
      setLoading(false);
    }
  };

  useImperativeHandle(ref, () => ({ toggle: handleToggle }));

  const copyText = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  if (!open) return null;

  return (
    <div className="mt-2 max-w-2xl space-y-2">
      {loading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Loading citations...
        </div>
      )}
      {data && (
        <>
          <div
            onClick={() => copyText(data.full, "full")}
            className="rounded-md bg-muted/50 p-3 text-sm text-foreground/80 leading-relaxed cursor-pointer hover:bg-muted transition-colors"
            title="Click to copy"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">Reference</span>
              {copiedField === "full" ? (
                <span className="text-xs text-green-600 flex items-center gap-1"><Check className="h-3 w-3" />Copied</span>
              ) : (
                <span className="text-xs text-muted-foreground flex items-center gap-1"><Copy className="h-3 w-3" />Click to copy</span>
              )}
            </div>
            <p className="whitespace-pre-wrap">{data.full}</p>
          </div>

          <div
            onClick={() => copyText(data.bibtex, "bibtex")}
            className="rounded-md bg-muted/50 p-3 font-mono text-xs text-foreground/80 cursor-pointer hover:bg-muted transition-colors"
            title="Click to copy"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground font-sans">BibTeX</span>
              {copiedField === "bibtex" ? (
                <span className="text-xs text-green-600 flex items-center gap-1 font-sans"><Check className="h-3 w-3" />Copied</span>
              ) : (
                <span className="text-xs text-muted-foreground flex items-center gap-1 font-sans"><Copy className="h-3 w-3" />Click to copy</span>
              )}
            </div>
            <pre className="whitespace-pre-wrap">{data.bibtex}</pre>
          </div>
        </>
      )}
    </div>
  );
});

// AI-powered result card (with explanation + stance)
function AIResultCard({ item, onOpenPdf, selected, onToggleSelect }: { item: ReferenceResult; onOpenPdf: (id: string, title: string) => void; selected: boolean; onToggleSelect: () => void }) {
  const { paper } = item;
  const authors = paper.authors.map((a) => a.name).join(", ");
  const pct = item.score != null ? Math.round(item.score * 100) : null;
  const citePanelRef = useRef<{ toggle: () => void }>(null);

  return (
    <div className="max-w-2xl py-4 flex gap-3">
      <button
        onClick={onToggleSelect}
        className={`mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
          selected
            ? "border-primary bg-primary text-white"
            : "border-border hover:border-primary/50"
        }`}
      >
        {selected && <Check className="h-3 w-3" />}
      </button>
      <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {authors}
        {paper.year ? ` · ${paper.year}` : ""}
        {pct != null && <span className="text-primary">{pct}% match</span>}
        <StanceBadge stance={item.stance} />
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
      <div className="flex items-center gap-3 mt-2">
        <button
          onClick={() => citePanelRef.current?.toggle()}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Copy className="h-3 w-3" />
          Cite
        </button>
        <button
          onClick={() => onOpenPdf(paper.id, paper.title)}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <FileText className="h-3 w-3" />
          PDF
        </button>
      </div>
      <CitePanel ref={citePanelRef} paperId={paper.id} />
      </div>
    </div>
  );
}

// Regular search result card (with abstract context)
function SearchResultCard({ item, onOpenPdf, selected, onToggleSelect }: { item: SearchResultItem; onOpenPdf: (id: string, title: string) => void; selected: boolean; onToggleSelect: () => void }) {
  const { paper } = item;
  const authors = paper.authors.map((a) => a.name).join(", ");
  const pct = item.score != null ? Math.round(item.score * 100) : null;
  const citePanelRef = useRef<{ toggle: () => void }>(null);

  return (
    <div className="max-w-2xl py-4 flex gap-3">
      <button
        onClick={onToggleSelect}
        className={`mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
          selected
            ? "border-primary bg-primary text-white"
            : "border-border hover:border-primary/50"
        }`}
      >
        {selected && <Check className="h-3 w-3" />}
      </button>
      <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {authors}
        {paper.year ? ` · ${paper.year}` : ""}
        {pct != null && <span className="text-primary">{pct}% relevance</span>}
      </div>
      <h3 className="text-lg text-primary mt-0.5 leading-snug">
        {paper.title}
      </h3>
      {paper.abstract && (
        <p className="text-sm text-foreground/70 mt-1 leading-relaxed line-clamp-3">
          {paper.abstract}
        </p>
      )}
      {paper.ai_summary && !paper.abstract && (
        <p className="text-sm text-foreground/70 mt-1 leading-relaxed line-clamp-3">
          {paper.ai_summary}
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
      <div className="flex items-center gap-3 mt-2">
        <button
          onClick={() => citePanelRef.current?.toggle()}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Copy className="h-3 w-3" />
          Cite
        </button>
        <button
          onClick={() => onOpenPdf(paper.id, paper.title)}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <FileText className="h-3 w-3" />
          PDF
        </button>
      </div>
      <CitePanel ref={citePanelRef} paperId={paper.id} />
      </div>
    </div>
  );
}

// AI toggle switch
const AI_LOADING_MESSAGES = [
  "Searching embeddings...",
  "Finding relevant papers...",
  "Analyzing content...",
  "Why is this so slow?",
  "Are you using the Xuxa PC?",
  "Are you sure you should be running this on this machine?",
  "Maybe you have time to make one (or maybe two) coffees before the results pop up",
  "You could probably go to YouTube and watch a video while waiting",
  "How is the weather today?",
  "The summer will probably be hot this year",
  "Et la famille, ça va?",
  "Have you tried turning it off and on again?",
  "Still working on it... probably",
  "The hamster powering the CPU needs a break",
  "Maybe it's time to invest in a GPU",
  "I'm not slow, I'm just thorough",
  "Fun fact: light travels 300,000 km/s. This model doesn't.",
  "Did you remember to water your plants today?",
  "This is a good time to stretch your legs",
  "Have you considered that the answer might be 42?",
  "Plot twist: the paper you need hasn't been written yet",
  "The embeddings are embedding... deeply",
  "At least it's not a fax machine",
  "Patience is a virtue. Or so they say.",
  "If you're reading this, the model is still thinking",
  "Maybe try a smaller model? Just a thought.",
  "Your CPU is doing its best. Be kind.",
  "Almost there... probably... maybe...",
];

function AILoadingIndicator() {
  const [msgIndex, setMsgIndex] = useState(0);
  const [dots, setDots] = useState(0);

  useEffect(() => {
    // Start with the first 3 real messages, then shuffle the rest
    const serious = AI_LOADING_MESSAGES.slice(0, 3);
    const jokes = AI_LOADING_MESSAGES.slice(3).sort(() => Math.random() - 0.5);
    const order = [...serious, ...jokes];

    let idx = 0;
    let timeout: ReturnType<typeof setTimeout>;
    const scheduleNext = () => {
      const delay = 3000 + Math.random() * 3000;
      timeout = setTimeout(() => {
        idx = (idx + 1) % order.length;
        setMsgIndex(AI_LOADING_MESSAGES.indexOf(order[idx]));
        scheduleNext();
      }, delay);
    };
    scheduleNext();
    const dotTimer = setInterval(() => {
      setDots((d) => (d + 1) % 4);
    }, 500);
    return () => { clearTimeout(timeout); clearInterval(dotTimer); };
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="relative h-5 w-5">
          <Sparkles className="h-5 w-5 text-purple-500 animate-pulse" />
        </div>
        <span className="text-sm text-purple-700">
          {AI_LOADING_MESSAGES[msgIndex]}{".".repeat(dots)}
        </span>
      </div>
      <div className="h-1 w-48 rounded-full bg-purple-100 overflow-hidden">
        <div className="h-full bg-purple-400 rounded-full animate-progress" />
      </div>
    </div>
  );
}

type AIModel = { id: string; provider: string; model: string; local: boolean };

function AIToggle({
  enabled,
  onChange,
  models,
  selectedModel,
  onSelectModel,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  models: AIModel[];
  selectedModel: string | null;
  onSelectModel: (id: string) => void;
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

  const current = models.find((m) => m.id === selectedModel) ?? models[0];
  const displayName = current?.model ?? "AI";

  return (
    <div ref={ref} className="relative inline-flex items-center gap-1">
      <button
        type="button"
        onClick={() => onChange(!enabled)}
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
          enabled
            ? "bg-purple-100 text-purple-700 border border-purple-200"
            : "border border-border text-muted-foreground hover:text-foreground"
        }`}
        title={enabled ? `AI: ${displayName}` : "AI analysis disabled"}
      >
        <Sparkles className={`h-3.5 w-3.5 ${enabled ? "text-purple-500" : ""}`} />
        <span className="text-xs font-medium">AI</span>
        <div
          className={`relative h-4 w-7 rounded-full transition-colors ${
            enabled ? "bg-purple-500" : "bg-border"
          }`}
        >
          <div
            className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${
              enabled ? "translate-x-3.5" : "translate-x-0.5"
            }`}
          />
        </div>
      </button>
      {enabled && models.length > 0 && (
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="inline-flex items-center gap-1 rounded-full border border-purple-200 bg-purple-50 px-2 py-1 text-xs text-purple-700 hover:bg-purple-100 transition-colors"
        >
          {displayName}
          {models.length > 1 && <ChevronDown className="h-3 w-3" />}
        </button>
      )}
      {open && models.length > 1 && (
        <div className="absolute top-full right-0 z-20 mt-1 min-w-[180px] rounded-lg border border-border bg-white shadow-lg overflow-hidden">
          {models.map((m) => (
            <button
              type="button"
              key={m.id}
              onClick={() => { onSelectModel(m.id); setOpen(false); }}
              className={`flex w-full items-center justify-between px-3 py-2 text-sm text-left hover:bg-muted transition-colors ${
                m.id === selectedModel ? "font-medium text-foreground" : "text-muted-foreground"
              }`}
            >
              <span>{m.model}</span>
              <span className="text-xs opacity-50">{m.local ? "local" : m.provider}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function flattenCollections(cols: PaperCollection[], depth = 0): { col: PaperCollection; depth: number }[] {
  const result: { col: PaperCollection; depth: number }[] = [];
  for (const c of cols) {
    result.push({ col: c, depth });
    if (c.children) result.push(...flattenCollections(c.children, depth + 1));
  }
  return result;
}

function CollectionSelector({
  collections,
  selectedIds,
  onToggle,
  onClear,
}: {
  collections: PaperCollection[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onClear: () => void;
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

  const flat = flattenCollections(collections);
  if (flat.length === 0) return null;

  const selectedNames = flat
    .filter(({ col }) => selectedIds.has(col.id))
    .map(({ col }) => col.name);

  const label = selectedNames.length === 0
    ? "All papers"
    : selectedNames.length <= 2
      ? selectedNames.join(", ")
      : `${selectedNames.length} collections`;

  return (
    <div ref={ref} className="relative inline-block">
      <div className="inline-flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
            selectedIds.size > 0
              ? "bg-primary/10 text-primary border border-primary/20"
              : "border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
          }`}
        >
          <FolderOpen className="h-3.5 w-3.5" />
          {label}
          <ChevronDown className="h-3 w-3" />
        </button>
        {selectedIds.size > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {open && (
        <div className="absolute z-20 mt-1 min-w-[220px] max-h-64 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
          {flat.map(({ col: c, depth }) => (
            <button
              type="button"
              key={c.id}
              onClick={() => onToggle(c.id)}
              className="flex w-full items-center gap-2 py-2 text-sm text-left hover:bg-muted transition-colors"
              style={{ paddingLeft: `${12 + depth * 16}px`, paddingRight: 12 }}
            >
              <div className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border transition-colors ${
                selectedIds.has(c.id)
                  ? "border-primary bg-primary text-white"
                  : "border-border"
              }`}>
                {selectedIds.has(c.id) && <Check className="h-2.5 w-2.5" />}
              </div>
              <span className="flex-1">{c.name}</span>
              <span className="text-xs opacity-60">{c.paper_count}</span>
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
      {search.collection_name && (
        <span className="text-xs text-muted-foreground/60 shrink-0">
          {search.collection_name}
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

function PdfViewer({
  paperId,
  title,
  onClose,
}: {
  paperId: string;
  title: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/60" onClick={onClose}>
      <div
        className="flex-1 flex flex-col m-4 md:m-8 rounded-lg overflow-hidden bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/50">
          <p className="text-sm font-medium truncate flex-1 mr-4">{title}</p>
          <div className="flex items-center gap-2">
            <a
              href={getPdfUrl(paperId)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              title="Open in new tab"
            >
              <Maximize2 className="h-4 w-4" />
            </a>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <iframe
          src={getPdfUrl(paperId)}
          className="flex-1 w-full"
          title={title}
        />
      </div>
    </div>
  );
}

const HISTORY_KEY = "reflens-search-history";
const MAX_HISTORY = 20;

function getHistory(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch { return []; }
}

function addToHistory(query: string) {
  const history = getHistory().filter((q) => q !== query);
  history.unshift(query);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
}

function removeFromHistory(query: string) {
  const history = getHistory().filter((q) => q !== query);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

export default function HomePage() {
  const [input, setInput] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedColIds, setSelectedColIds] = useState<Set<string>>(new Set());
  const [pdfViewer, setPdfViewer] = useState<{ id: string; title: string } | null>(null);
  const [aiEnabled, _setAiEnabled] = useState(false);
  const aiRef = useRef(false);
  const setAiEnabled = (v: boolean) => { aiRef.current = v; _setAiEnabled(v); };
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [cachedResults, setCachedResults] = useState<ReferenceResult[] | null>(null);
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const [bulkBibtexCopied, setBulkBibtexCopied] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const searchStartRef = useRef<number>(0);
  const historyRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [aiSearching, setAiSearching] = useState(false);
  const [aiSearchResults, setAiSearchResults] = useState<ReferenceResult[] | null>(null);
  const [aiSearchError, setAiSearchError] = useState(false);
  const qc = useQueryClient();

  // Load history on mount
  useEffect(() => { setHistory(getHistory()); }, []);

  // Close history dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (historyRef.current && !historyRef.current.contains(e.target as Node)) setShowHistory(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Debounce input for regular search mode
  useEffect(() => {
    if (!aiEnabled && hasSearched) {
      const timer = setTimeout(() => setDebouncedQuery(input.trim()), 300);
      return () => clearTimeout(timer);
    }
  }, [input, aiEnabled, hasSearched]);

  const activeColIds = selectedColIds.size > 0 ? Array.from(selectedColIds) : undefined;

  // Regular search
  const { data: regularSearchData, isLoading: regularSearchLoading } = useSearch(
    !aiEnabled ? debouncedQuery : "",
    activeColIds
  );

  const { data: collectionsData } = useQuery({
    queryKey: ["collections"],
    queryFn: () => api.collections.list(),
  });

  const { data: savedSearchesData } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => api.savedSearches.list(),
  });

  const { data: aiInfo } = useQuery({
    queryKey: ["ai-info"],
    queryFn: () => api.aiInfo(),
  });
  const availableModels: AIModel[] = aiInfo?.models ?? [];
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  // Set default model on first load
  useEffect(() => {
    if (aiInfo?.default && !selectedModelId) setSelectedModelId(aiInfo.default);
  }, [aiInfo, selectedModelId]);

  const saveMutation = useMutation({
    mutationFn: ({ text, collectionIds, results }: { text: string; collectionIds?: string[]; results?: ReferenceResult[] }) =>
      api.savedSearches.save(text, collectionIds, results),
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

  const collections = collectionsData?.collections ?? [];
  const savedSearches = savedSearchesData?.searches ?? [];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const useAi = aiRef.current;
    addToHistory(input.trim());
    setHistory(getHistory());
    setShowHistory(false);
    setHasSearched(true);
    setSaved(false);
    setCachedResults(null);
    setSelectedPaperIds(new Set());
    setSearchTime(null);
    searchStartRef.current = performance.now();
    if (useAi) {
      setDebouncedQuery("");
      // Abort any previous request
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setAiSearching(true);
      setAiSearchResults(null);
      setAiSearchError(false);
      api.findReferences({
        text: input.trim(),
        limit: 10,
        explain: true,
        collection_ids: activeColIds,
        model_id: selectedModelId ?? undefined,
      }, controller.signal)
        .then((data) => {
          if (!controller.signal.aborted) {
            setAiSearchResults(data.results);
            setAiSearching(false);
          }
        })
        .catch((err) => {
          if (!controller.signal.aborted) {
            setAiSearchError(true);
            setAiSearching(false);
          }
        });
    } else {
      setAiSearchResults(null);
      setDebouncedQuery(input.trim());
    }
  };

  const togglePaperId = (id: string) => {
    setSelectedPaperIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const copySelectedBibtex = async () => {
    if (selectedPaperIds.size === 0) return;
    try {
      const entries = await Promise.all(
        Array.from(selectedPaperIds).map((id) => api.papers.bibtex(id))
      );
      await navigator.clipboard.writeText(entries.join("\n\n"));
      setBulkBibtexCopied(true);
      setTimeout(() => setBulkBibtexCopied(false), 2500);
    } catch { /* ignore */ }
  };

  const toggleCollectionId = (id: string) => {
    setSelectedColIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const loadSavedSearch = (search: SavedSearch) => {
    setInput(search.text);
    setSelectedColIds(search.collection_id ? new Set([search.collection_id]) : new Set());
    setHasSearched(true);
    setSaved(true);
    setAiEnabled(true);
    if (search.results && search.results.length > 0) {
      setCachedResults(search.results);
    } else {
      setCachedResults(null);
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setAiSearching(true);
      setAiSearchResults(null);
      api.findReferences({
        text: search.text,
        limit: 10,
        explain: true,
        collection_ids: search.collection_id ? [search.collection_id] : undefined,
        model_id: selectedModelId ?? undefined,
      }, controller.signal)
        .then((data) => { if (!controller.signal.aborted) { setAiSearchResults(data.results); setAiSearching(false); } })
        .catch(() => { if (!controller.signal.aborted) { setAiSearching(false); } });
    }
  };

  // AI results
  const aiResults = cachedResults ?? aiSearchResults;
  const isAiSearchPending = !cachedResults && aiSearching;

  // Regular results
  const regularResults = regularSearchData?.results ?? null;

  // Stop timer when results arrive
  useEffect(() => {
    if (searchStartRef.current > 0 && !isAiSearchPending && !regularSearchLoading) {
      const elapsed = (performance.now() - searchStartRef.current) / 1000;
      if (aiResults || regularResults) {
        setSearchTime(elapsed);
        searchStartRef.current = 0;
      }
    }
  }, [isAiSearchPending, regularSearchLoading, aiResults, regularResults]);

  // Landing state: centered logo + search
  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4">
        <h1 className="text-5xl font-light tracking-tight text-foreground mb-8">
          Ref<span className="text-primary font-normal">Lens</span>
        </h1>
        <form onSubmit={handleSearch} className="w-full max-w-xl space-y-3">
          <div className="relative" ref={historyRef}>
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => { if (history.length > 0) setShowHistory(true); }}
              placeholder={
                aiEnabled
                  ? "Paste a claim to find supporting (or contradicting) references..."
                  : "Search papers by title, content, or keywords..."
              }
              className="w-full rounded-full border border-border bg-white px-12 py-3.5 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              autoFocus
            />
            {showHistory && history.length > 0 && (
              <div className="absolute z-20 mt-1 w-full max-h-64 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
                <div className="px-3 py-1.5 text-xs text-muted-foreground/60 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Recent searches
                </div>
                {history
                  .filter((q) => !input || q.toLowerCase().includes(input.toLowerCase()))
                  .map((q) => (
                  <div key={q} className="group flex items-center hover:bg-muted transition-colors">
                    <button
                      type="button"
                      onClick={() => {
                        setInput(q);
                        setShowHistory(false);
                      }}
                      className="flex-1 px-3 py-2 text-sm text-left text-muted-foreground hover:text-foreground truncate"
                    >
                      {q}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        removeFromHistory(q);
                        setHistory(getHistory());
                      }}
                      className="opacity-0 group-hover:opacity-100 px-2 text-muted-foreground hover:text-destructive transition-all"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center justify-center gap-3">
            <AIToggle enabled={aiEnabled} onChange={setAiEnabled} models={availableModels} selectedModel={selectedModelId} onSelectModel={setSelectedModelId} />
            <CollectionSelector
              collections={collections}
              selectedIds={selectedColIds}
              onToggle={toggleCollectionId}
              onClear={() => setSelectedColIds(new Set())}
            />
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
        <div className="flex items-center gap-3 px-6 py-3 max-w-4xl">
          <Link
            href="/"
            onClick={(e) => {
              e.preventDefault();
              setHasSearched(false);
              setInput("");
              setSaved(false);
              setCachedResults(null);
              setDebouncedQuery("");
            }}
            className="text-xl font-light tracking-tight text-foreground shrink-0"
          >
            Ref<span className="text-primary font-normal">Lens</span>
          </Link>
          <form onSubmit={handleSearch} className="flex-1 max-w-xl">
            <div className="relative" ref={historyRef}>
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={input}
                onChange={(e) => { setInput(e.target.value); setSaved(false); setCachedResults(null); }}
                onFocus={() => { if (history.length > 0) setShowHistory(true); }}
                placeholder={aiEnabled ? "Paste a claim..." : "Search papers..."}
                className="w-full rounded-full border border-border bg-white pl-10 pr-4 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                autoFocus
              />
              {showHistory && history.length > 0 && (
                <div className="absolute z-20 mt-1 w-full max-h-48 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
                  {history
                    .filter((q) => !input || q.toLowerCase().includes(input.toLowerCase()))
                    .map((q) => (
                    <div key={q} className="group flex items-center hover:bg-muted transition-colors">
                      <button
                        type="button"
                        onClick={() => { setInput(q); setShowHistory(false); }}
                        className="flex-1 px-3 py-2 text-sm text-left text-muted-foreground hover:text-foreground truncate"
                      >
                        {q}
                      </button>
                      <button
                        type="button"
                        onClick={() => { removeFromHistory(q); setHistory(getHistory()); }}
                        className="opacity-0 group-hover:opacity-100 px-2 text-muted-foreground hover:text-destructive transition-all"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </form>
          <AIToggle enabled={aiEnabled} models={availableModels} selectedModel={selectedModelId} onSelectModel={setSelectedModelId} onChange={(v) => {
            setAiEnabled(v);
            setCachedResults(null);
            if (v) {
              setDebouncedQuery("");
            } else {
              if (abortRef.current) abortRef.current.abort();
              setAiSearching(false);
              setAiSearchResults(null);
              if (input.trim()) setDebouncedQuery(input.trim());
            }
          }} />
          <CollectionSelector
            collections={collections}
            selectedIds={selectedColIds}
            onToggle={toggleCollectionId}
            onClear={() => setSelectedColIds(new Set())}
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
        {/* AI mode */}
        {aiEnabled && (
          <>
            {isAiSearchPending && (
              <div className="py-8 space-y-4">
                <AILoadingIndicator />
                <button
                  onClick={() => { if (abortRef.current) abortRef.current.abort(); setAiSearching(false); setAiSearchResults(null); setSearchTime(null); }}
                  className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}

            {aiResults && aiResults.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-muted-foreground">
                    <Sparkles className="h-3 w-3 text-purple-500 inline mr-1" />
                    {aiResults.length} reference{aiResults.length !== 1 ? "s" : ""} found
                    {activeColIds ? ` in ${activeColIds.length} collection${activeColIds.length !== 1 ? "s" : ""}` : ""}
                    {searchTime != null && <span className="opacity-50"> ({searchTime.toFixed(2)}s)</span>}
                  </p>
                  <div className="flex items-center gap-2">
                    {selectedPaperIds.size > 0 && (
                      <button
                        onClick={copySelectedBibtex}
                        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                          bulkBibtexCopied
                            ? "text-green-600"
                            : "border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                        }`}
                      >
                        {bulkBibtexCopied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                        {bulkBibtexCopied ? `${selectedPaperIds.size} copied` : `Copy ${selectedPaperIds.size} BibTeX`}
                      </button>
                    )}
                    <button
                      onClick={() => saveMutation.mutate({ text: input.trim(), collectionIds: activeColIds, results: aiResults })}
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
                </div>
                <div className="divide-y divide-border">
                  {aiResults.map((item) => (
                    <AIResultCard key={item.paper.id} item={item} onOpenPdf={(id, title) => setPdfViewer({ id, title })} selected={selectedPaperIds.has(item.paper.id)} onToggleSelect={() => togglePaperId(item.paper.id)} />
                  ))}
                </div>
              </div>
            )}

            {aiResults && aiResults.length === 0 && (
              <p className="text-sm text-muted-foreground py-8">
                No matching references found. Try rephrasing your claim
                {activeColIds ? " or searching all papers." : "."}
              </p>
            )}

            {aiSearchError && !cachedResults && (
              <p className="text-sm text-destructive py-8">
                Something went wrong. Please try again.
              </p>
            )}
          </>
        )}

        {/* Regular mode */}
        {!aiEnabled && (
          <>
            {regularSearchLoading && debouncedQuery && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching...
                <button
                  onClick={() => { setDebouncedQuery(""); setSearchTime(null); }}
                  className="ml-2 rounded-full border border-border px-3 py-0.5 text-xs hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}

            {regularResults && regularResults.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-muted-foreground">
                    {regularResults.length} result{regularResults.length !== 1 ? "s" : ""} for &quot;{regularSearchData?.query}&quot;
                    {searchTime != null && <span className="opacity-50"> ({searchTime.toFixed(2)}s)</span>}
                  </p>
                  {selectedPaperIds.size > 0 && (
                    <button
                      onClick={copySelectedBibtex}
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                        bulkBibtexCopied
                          ? "text-green-600"
                          : "border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                      }`}
                    >
                      {bulkBibtexCopied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      {bulkBibtexCopied ? `${selectedPaperIds.size} copied` : `Copy ${selectedPaperIds.size} BibTeX`}
                    </button>
                  )}
                </div>
                <div className="divide-y divide-border">
                  {regularResults.map((item) => (
                    <SearchResultCard key={item.paper.id} item={item} onOpenPdf={(id, title) => setPdfViewer({ id, title })} selected={selectedPaperIds.has(item.paper.id)} onToggleSelect={() => togglePaperId(item.paper.id)} />
                  ))}
                </div>
              </div>
            )}

            {regularResults && regularResults.length === 0 && debouncedQuery && (
              <p className="text-sm text-muted-foreground py-8">
                No results for &quot;{debouncedQuery}&quot;. Try different keywords.
              </p>
            )}

            {!debouncedQuery && (
              <p className="text-sm text-muted-foreground py-8">
                Type a query and press Enter to search your library.
              </p>
            )}
          </>
        )}
      </div>

      {/* PDF Viewer Modal */}
      {pdfViewer && (
        <PdfViewer
          paperId={pdfViewer.id}
          title={pdfViewer.title}
          onClose={() => setPdfViewer(null)}
        />
      )}
    </div>
  );
}
