"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Search,
  Upload,
  FileUp,
  Loader2,
  Sparkles,
  ChevronDown,
  ChevronRight,
  Check,
  Trash2,
  CheckCircle2,
  XCircle,
  X,
  FolderOpen,
  FolderPlus,
  Plus,
  FileText,
} from "lucide-react";
import { useDropzone } from "react-dropzone";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, getPdfUrl } from "@/lib/api";
import { usePapers, useDeletePaper, useBulkAction } from "@/hooks/use-papers";
import { useUpload } from "@/hooks/use-upload";
import { useSearch } from "@/hooks/use-search";
import { Pagination } from "@/components/shared/pagination";
import type { PaperSummary, PaperUploadResponse, PaperGroup, Tag, TaskStatusResponse } from "@/lib/types";

const PAGE_SIZE = 20;

// Tag search/selector component
function TagSelector({
  allTags,
  selectedTags,
  onToggle,
  onClear,
}: {
  allTags: Tag[];
  selectedTags: Tag[];
  onToggle: (tag: Tag) => void;
  onClear: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const selectedIds = new Set(selectedTags.map((t) => t.id));
  const filtered = allTags.filter(
    (t) => !selectedIds.has(t.id) && t.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div ref={ref} className="relative">
      <div
        className="flex flex-wrap items-center gap-1.5 rounded-full border border-border bg-white px-3 py-1.5 cursor-text min-h-[36px]"
        onClick={() => setOpen(true)}
      >
        {selectedTags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 rounded-full bg-foreground text-background px-2.5 py-0.5 text-xs font-medium"
          >
            {tag.name}
            <button
              onClick={(e) => { e.stopPropagation(); onToggle(tag); }}
              className="hover:opacity-70"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder={selectedTags.length === 0 ? "Filter by tags..." : ""}
          className="flex-1 min-w-[100px] bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
        {selectedTags.length > 0 && (
          <button
            onClick={(e) => { e.stopPropagation(); onClear(); }}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {open && filtered.length > 0 && (
        <div className="absolute z-20 mt-1 w-full max-h-48 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
          {filtered.map((tag) => (
            <button
              key={tag.id}
              onClick={() => { onToggle(tag); setSearch(""); }}
              className="flex w-full items-center px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
            >
              {tag.name}
            </button>
          ))}
        </div>
      )}

      {open && search && filtered.length === 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-border bg-white shadow-lg p-3">
          <p className="text-sm text-muted-foreground">No matching tags</p>
        </div>
      )}
    </div>
  );
}

// Group manager: dropdown to add selected papers to a group, or create new
function GroupActions({
  selectedIds,
  groups,
}: {
  selectedIds: Set<string>;
  groups: PaperGroup[];
}) {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setCreating(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (creating && inputRef.current) inputRef.current.focus();
  }, [creating]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 2500);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = (groupName: string, count: number) => {
    setToast(`${count} paper${count !== 1 ? "s" : ""} added to "${groupName}"`);
  };

  const addToGroup = useMutation({
    mutationFn: ({ groupId, paperIds }: { groupId: string; paperIds: string[] }) =>
      api.groups.addPapers(groupId, paperIds),
    onSuccess: (_data, { groupId, paperIds }) => {
      qc.invalidateQueries({ queryKey: ["groups"] });
      qc.invalidateQueries({ queryKey: ["group-detail"] });
      const group = groups.find((g) => g.id === groupId);
      showToast(group?.name ?? "group", paperIds.length);
    },
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreateGroup = async () => {
    if (!newName.trim() || isSubmitting) return;
    setIsSubmitting(true);
    const paperIds = Array.from(selectedIds);
    const name = newName.trim();
    try {
      const group = await api.groups.create(name);
      await api.groups.addPapers(group.id, paperIds);
      qc.invalidateQueries({ queryKey: ["groups"] });
      qc.invalidateQueries({ queryKey: ["group-detail"] });
      showToast(group.name, paperIds.length);
      setNewName("");
      setCreating(false);
      setOpen(false);
    } catch {
      // ignore
    }
    setIsSubmitting(false);
  };

  if (selectedIds.size === 0) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs font-medium hover:bg-muted transition-colors"
      >
        <FolderPlus className="h-3 w-3" />
        Add to group
        <ChevronDown className="h-3 w-3" />
      </button>

      {/* Toast notification */}
      {toast && (
        <div className="absolute right-0 -top-10 z-30 whitespace-nowrap rounded-lg bg-foreground text-background px-3 py-1.5 text-xs font-medium shadow-lg animate-fade-in">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {toast}
          </div>
        </div>
      )}

      {open && (
        <div className="absolute right-0 z-20 mt-1 min-w-[200px] rounded-lg border border-border bg-white shadow-lg">
          {groups.map((g) => (
            <button
              key={g.id}
              onClick={() => {
                addToGroup.mutate({ groupId: g.id, paperIds: Array.from(selectedIds) });
                setOpen(false);
              }}
              className="flex w-full items-center justify-between px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
            >
              <span>{g.name}</span>
              <span className="text-xs text-muted-foreground">{g.paper_count}</span>
            </button>
          ))}

          {creating ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleCreateGroup();
              }}
              className="flex items-center gap-1 px-3 py-2 border-t border-border"
            >
              <input
                ref={inputRef}
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onMouseDown={(e) => e.stopPropagation()}
                placeholder="Group name..."
                className="flex-1 text-sm bg-transparent outline-none"
                disabled={isSubmitting}
              />
              <button
                type="submit"
                disabled={!newName.trim() || isSubmitting}
                className="text-primary disabled:opacity-30"
              >
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              </button>
            </form>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setCreating(true);
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-left text-primary hover:bg-muted transition-colors border-t border-border"
            >
              <Plus className="h-3.5 w-3.5" />
              New group
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// Upload area
function UploadZone() {
  const upload = useUpload();
  const [results, setResults] = useState<
    { file: string; status: "success" | "error"; data?: PaperUploadResponse; error?: string }[]
  >([]);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploading(true);
      const newResults: typeof results = [];
      for (const file of acceptedFiles) {
        try {
          const data = await upload.mutateAsync(file);
          newResults.push({ file: file.name, status: "success", data });
        } catch (err) {
          newResults.push({
            file: file.name,
            status: "error",
            error: err instanceof Error ? err.message : "Upload failed",
          });
        }
      }
      setResults((prev) => [...newResults, ...prev]);
      setUploading(false);
    },
    [upload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    disabled: uploading,
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`flex items-center justify-center rounded-lg border-2 border-dashed py-8 px-6 transition-colors cursor-pointer ${
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/40"
        } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Uploading...
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {isDragActive ? (
              <FileUp className="h-5 w-5 text-primary" />
            ) : (
              <Upload className="h-5 w-5" />
            )}
            <span>{isDragActive ? "Drop PDFs here" : "Drop PDFs here or click to browse"}</span>
          </div>
        )}
      </div>

      {results.length > 0 && (
        <div className="space-y-1.5">
          {results.map((r, i) => (
            <div key={i} className="flex items-center gap-2 text-sm px-1">
              {r.status === "success" ? (
                <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 text-destructive shrink-0" />
              )}
              <span className="truncate">
                {r.status === "success" ? r.data?.title : r.file}
              </span>
              {r.status === "error" && (
                <span className="text-xs text-destructive">{r.error}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Inline DOI editor
function DoiField({ paper }: { paper: PaperSummary }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(paper.doi ?? "");
  const [saved, setSaved] = useState(false);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: (doi: string) => api.papers.update(paper.id, { doi: doi || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["group-detail"] });
      setSaved(true);
      setEditing(false);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  if (!editing) {
    return (
      <div className="flex items-center gap-2 mt-2">
        <span className="text-xs text-muted-foreground">DOI:</span>
        {paper.doi ? (
          <span className="text-xs text-foreground/70">{paper.doi}</span>
        ) : (
          <span className="text-xs text-muted-foreground italic">not set</span>
        )}
        <button
          onClick={() => { setValue(paper.doi ?? ""); setEditing(true); }}
          className="text-xs text-primary hover:underline"
        >
          {paper.doi ? "edit" : "add"}
        </button>
        {saved && <span className="text-xs text-green-600">saved</span>}
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate(value.trim());
      }}
      className="flex items-center gap-2 mt-2"
    >
      <span className="text-xs text-muted-foreground">DOI:</span>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="10.1234/example"
        className="flex-1 max-w-xs rounded border border-border bg-white px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
        autoFocus
      />
      <button
        type="submit"
        disabled={mutation.isPending}
        className="text-xs text-primary hover:underline disabled:opacity-50"
      >
        {mutation.isPending ? "saving..." : "save"}
      </button>
      <button
        type="button"
        onClick={() => setEditing(false)}
        className="text-xs text-muted-foreground hover:text-foreground"
      >
        cancel
      </button>
    </form>
  );
}

// Single paper row
function PaperRow({
  paper,
  selected,
  onToggle,
  onDelete,
}: {
  paper: PaperSummary;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-border last:border-b-0">
      <div className="flex items-center gap-3 py-3 px-1">
        <button
          onClick={onToggle}
          className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
            selected
              ? "border-primary bg-primary text-white"
              : "border-border hover:border-primary/50"
          }`}
        >
          {selected && <Check className="h-3 w-3" />}
        </button>

        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate" title={paper.title}>{paper.title}</p>
          <p className="text-xs text-muted-foreground truncate">
            {paper.authors.map((a) => a.name).join(", ")}
            {paper.year ? ` · ${paper.year}` : ""}
          </p>
        </div>

        {paper.tags.length > 0 && (
          <div className="hidden sm:flex flex-wrap gap-1 shrink-0">
            {paper.tags.slice(0, 3).map((t) => (
              <span
                key={t.id}
                className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground"
              >
                {t.tag_name}
              </span>
            ))}
            {paper.tags.length > 3 && (
              <span className="text-xs text-muted-foreground">+{paper.tags.length - 3}</span>
            )}
          </div>
        )}

        {paper.ai_summary && (
          <span className="text-xs text-green-600 shrink-0">summarized</span>
        )}

        <button
          onClick={onDelete}
          className="text-muted-foreground hover:text-destructive transition-colors shrink-0"
          title="Delete"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {expanded && (
        <div className="pl-12 pr-4 pb-3">
          {paper.abstract ? (
            <p className="text-sm text-foreground/70 leading-relaxed">{paper.abstract}</p>
          ) : (
            <p className="text-sm text-muted-foreground italic">No abstract available</p>
          )}
          <DoiField paper={paper} />
          <button
            onClick={() => window.open(getPdfUrl(paper.id), "_blank")}
            className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline"
          >
            <FileText className="h-3 w-3" />
            View PDF
          </button>
          {paper.ai_summary && (
            <div className="mt-2 rounded-md bg-muted/50 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">AI Summary</p>
              <p className="text-sm text-foreground/80 leading-relaxed">{paper.ai_summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Bulk action progress bar
function TaskProgress({
  label,
  status,
  onDismiss,
}: {
  label: string;
  status: TaskStatusResponse;
  onDismiss: () => void;
}) {
  const processed = status.completed + status.failed;
  const pct = status.total > 0 ? Math.round((processed / status.total) * 100) : 0;
  const isDone = status.status === "completed" || status.status === "failed";

  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground">
      <span>
        {isDone
          ? `${label}: ${status.completed} done${status.failed > 0 ? `, ${status.failed} failed` : ""}`
          : `${label}... ${processed}/${status.total}`}
      </span>
      {status.total > 0 && (
        <div className="h-1 w-32 rounded-full bg-border overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              isDone
                ? status.failed > 0 ? "bg-red-500" : "bg-green-500"
                : "bg-primary"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
      {isDone && (
        <button onClick={onDismiss} className="hover:text-foreground transition-colors">
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

// Group chips row
function GroupChips({
  groups,
  activeGroup,
  onSelect,
  onDelete,
}: {
  groups: PaperGroup[];
  activeGroup: string | null;
  onSelect: (id: string | null) => void;
  onDelete: (id: string) => void;
}) {
  if (groups.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <FolderOpen className="h-4 w-4 text-muted-foreground" />
      <button
        onClick={() => onSelect(null)}
        className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
          !activeGroup
            ? "bg-foreground text-background"
            : "border border-border text-muted-foreground hover:text-foreground"
        }`}
      >
        All
      </button>
      {groups.map((g) => (
        <button
          key={g.id}
          onClick={() => onSelect(g.id === activeGroup ? null : g.id)}
          onContextMenu={(e) => {
            e.preventDefault();
            if (confirm(`Delete group "${g.name}"? Papers won't be deleted.`)) {
              onDelete(g.id);
            }
          }}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            activeGroup === g.id
              ? "bg-foreground text-background"
              : "border border-border text-muted-foreground hover:text-foreground"
          }`}
          title={`${g.paper_count} papers (right-click to delete group)`}
        >
          {g.name}
          <span className="ml-1 opacity-60">{g.paper_count}</span>
        </button>
      ))}
    </div>
  );
}

export default function LibraryPage() {
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedTags, setSelectedTags] = useState<Tag[]>([]);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);
  const qc = useQueryClient();

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setSearchQuery(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const activeTagIds = selectedTags.map((t) => t.id);

  // Data fetching
  const { data: papersData, isLoading: loadingPapers } = usePapers(
    PAGE_SIZE,
    offset,
    activeTagIds.length > 0 ? activeTagIds : undefined
  );
  const { data: searchData, isLoading: loadingSearch } = useSearch(searchQuery);
  const { data: tagsData } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.tags.list(),
  });
  const { data: groupsData } = useQuery({
    queryKey: ["groups"],
    queryFn: () => api.groups.list(),
  });
  const { data: groupDetail } = useQuery({
    queryKey: ["group-detail", activeGroup],
    queryFn: () => api.groups.get(activeGroup!),
    enabled: !!activeGroup,
  });

  const deleteGroupMutation = useMutation({
    mutationFn: (id: string) => api.groups.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["groups"] });
      if (activeGroup) setActiveGroup(null);
    },
  });

  const deleteMutation = useDeletePaper();
  const summarizeAll = useBulkAction("summarize-all");
  const tagAll = useBulkAction("tag-all");

  const groups = groupsData?.groups ?? [];

  // Determine which papers to show
  const isSearching = searchQuery.length > 0;
  const isGroupFiltering = !!activeGroup;
  const displayPapers: PaperSummary[] = isSearching
    ? (searchData?.results.map((r) => r.paper) ?? [])
    : isGroupFiltering
      ? (groupDetail?.papers ?? [])
      : (papersData?.papers ?? []);
  const isLoading = isSearching ? loadingSearch : loadingPapers;

  const allSelected = displayPapers.length > 0 && displayPapers.every((p) => selectedIds.has(p.id));

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(displayPapers.map((p) => p.id)));
    }
  };

  const toggleTag = (tag: Tag) => {
    setSelectedTags((prev) =>
      prev.some((t) => t.id === tag.id)
        ? prev.filter((t) => t.id !== tag.id)
        : [...prev, tag]
    );
    setOffset(0);
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="border-b border-border bg-white sticky top-0 z-10">
        <div className="flex items-center gap-6 px-6 py-3 max-w-5xl mx-auto">
          <Link href="/" className="text-xl font-light tracking-tight text-foreground shrink-0">
            Ref<span className="text-primary font-normal">Lens</span>
          </Link>
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setActiveGroup(null);
                setOffset(0);
              }}
              placeholder="Search papers..."
              className="w-full rounded-full border border-border bg-white pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>
          <Link
            href="/"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            Search references
          </Link>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* Upload */}
        <UploadZone />

        {/* Groups */}
        {!isSearching && (
          <GroupChips
            groups={groups}
            activeGroup={activeGroup}
            onSelect={(id) => {
              setActiveGroup(id);
              setSelectedTags([]);
              setOffset(0);
            }}
            onDelete={(id) => deleteGroupMutation.mutate(id)}
          />
        )}

        {/* Tag selector */}
        {tagsData && tagsData.tags.length > 0 && !isSearching && !isGroupFiltering && (
          <TagSelector
            allTags={tagsData.tags}
            selectedTags={selectedTags}
            onToggle={toggleTag}
            onClear={() => { setSelectedTags([]); setOffset(0); }}
          />
        )}

        {/* Toolbar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={toggleAll}
              className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                allSelected
                  ? "border-primary bg-primary text-white"
                  : "border-border hover:border-primary/50"
              }`}
            >
              {allSelected && <Check className="h-3 w-3" />}
            </button>
            <span className="text-xs text-muted-foreground">
              {selectedIds.size > 0
                ? `${selectedIds.size} selected`
                : `${isSearching ? (searchData?.results.length ?? 0) : isGroupFiltering ? (groupDetail?.papers.length ?? 0) : (papersData?.total ?? 0)} papers`}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <GroupActions selectedIds={selectedIds} groups={groups} />

            {selectedIds.size > 0 && (
              <button
                onClick={() => summarizeAll.trigger()}
                disabled={summarizeAll.isPending || summarizeAll.isActive}
                className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 transition-colors"
              >
                <Sparkles className="h-3 w-3" />
                Summarize
              </button>
            )}
            {(summarizeAll.taskId && summarizeAll.status) && (
              <TaskProgress
                label="Summarizing"
                status={summarizeAll.status}
                onDismiss={summarizeAll.dismiss}
              />
            )}
            {(tagAll.taskId && tagAll.status) && (
              <TaskProgress
                label="Tagging"
                status={tagAll.status}
                onDismiss={tagAll.dismiss}
              />
            )}
          </div>
        </div>

        {/* Papers list */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : displayPapers.length === 0 ? (
          <p className="text-center py-12 text-sm text-muted-foreground">
            {isSearching
              ? `No results for "${searchQuery}"`
              : isGroupFiltering
                ? "No papers in this group yet."
                : selectedTags.length > 0
                  ? "No papers match all selected tags."
                  : "No papers yet. Upload a PDF to get started."}
          </p>
        ) : (
          <div className="border-t border-border">
            {displayPapers.map((paper) => (
              <PaperRow
                key={paper.id}
                paper={paper}
                selected={selectedIds.has(paper.id)}
                onToggle={() => toggleSelect(paper.id)}
                onDelete={() => deleteMutation.mutate(paper.id)}
              />
            ))}
          </div>
        )}

        {/* Pagination (only for non-search, non-group views) */}
        {!isSearching && !isGroupFiltering && papersData && (
          <Pagination
            total={papersData.total}
            limit={papersData.limit}
            offset={offset}
            onPageChange={setOffset}
          />
        )}
      </div>
    </div>
  );
}
