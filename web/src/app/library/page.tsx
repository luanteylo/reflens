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
// Folder upload uses native drag-and-drop API for directory traversal
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, getPdfUrl } from "@/lib/api";
import { usePapers, useDeletePaper, useBulkAction } from "@/hooks/use-papers";
import { useUpload } from "@/hooks/use-upload";
import { useSearch } from "@/hooks/use-search";
import { Pagination } from "@/components/shared/pagination";
import type { PaperSummary, PaperUploadResponse, PaperCollection, Tag, TaskStatusResponse } from "@/lib/types";

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
function CollectionActions({
  selectedIds,
  collections,
}: {
  selectedIds: Set<string>;
  collections: PaperCollection[];
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

  const addToCollection = useMutation({
    mutationFn: ({ colId, paperIds }: { colId: string; paperIds: string[] }) =>
      api.collections.addPapers(colId, paperIds),
    onSuccess: (_data, { colId, paperIds }) => {
      qc.invalidateQueries({ queryKey: ["collections"] });
      qc.invalidateQueries({ queryKey: ["collection-detail"] });
      const match = collections.find((g) => g.id === colId);
      showToast(match?.name ?? "collection", paperIds.length);
    },
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreateCollection = async () => {
    if (!newName.trim() || isSubmitting) return;
    setIsSubmitting(true);
    const paperIds = Array.from(selectedIds);
    const name = newName.trim();
    try {
      const col = await api.collections.create(name);
      await api.collections.addPapers(col.id, paperIds);
      qc.invalidateQueries({ queryKey: ["collections"] });
      qc.invalidateQueries({ queryKey: ["collection-detail"] });
      showToast(col?.name, paperIds.length);
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
        Add to collection
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

      {open && (() => {
        const flat: { col: PaperCollection; depth: number }[] = [];
        const flatten = (cols: PaperCollection[], d: number) => {
          for (const c of cols) { flat.push({ col: c, depth: d }); if (c.children) flatten(c.children, d + 1); }
        };
        flatten(collections, 0);
        return (
        <div className="absolute right-0 z-20 mt-1 min-w-[220px] max-h-64 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
          {flat.map(({ col: c, depth }) => (
            <button
              key={c.id}
              onClick={() => {
                addToCollection.mutate({ colId: c.id, paperIds: Array.from(selectedIds) });
                setOpen(false);
              }}
              className="flex w-full items-center justify-between py-2 text-sm text-left hover:bg-muted transition-colors"
              style={{ paddingLeft: `${12 + depth * 16}px`, paddingRight: 12 }}
            >
              <span>{c.name}</span>
              <span className="text-xs text-muted-foreground">{c.paper_count}</span>
            </button>
          ))}

          {creating ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleCreateCollection();
              }}
              className="flex items-center gap-1 px-3 py-2 border-t border-border"
            >
              <input
                ref={inputRef}
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onMouseDown={(e) => e.stopPropagation()}
                placeholder="Collection name..."
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
              New collection
            </button>
          )}
        </div>
        );
      })()}
    </div>
  );
}

// Recursively read files from a dropped directory entry
async function readEntries(entry: FileSystemEntry, path: string = ""): Promise<{ file: File; path: string }[]> {
  if (entry.isFile) {
    const fileEntry = entry as FileSystemFileEntry;
    return new Promise((resolve) => {
      fileEntry.file((f) => {
        if (f.name.toLowerCase().endsWith(".pdf")) {
          resolve([{ file: f, path }]);
        } else {
          resolve([]);
        }
      });
    });
  }
  if (entry.isDirectory) {
    const dirEntry = entry as FileSystemDirectoryEntry;
    const reader = dirEntry.createReader();
    const entries = await new Promise<FileSystemEntry[]>((resolve) => {
      const all: FileSystemEntry[] = [];
      const readBatch = () => {
        reader.readEntries((batch) => {
          if (batch.length === 0) { resolve(all); return; }
          all.push(...batch);
          readBatch();
        });
      };
      readBatch();
    });
    const subPath = path ? `${path}/${entry.name}` : entry.name;
    const results: { file: File; path: string }[] = [];
    for (const e of entries) {
      results.push(...(await readEntries(e, subPath)));
    }
    return results;
  }
  return [];
}

// Upload area with folder support
function UploadZone() {
  const upload = useUpload();
  const [results, setResults] = useState<
    { file: string; collection?: string; status: "success" | "error"; data?: PaperUploadResponse; error?: string }[]
  >([]);
  const [uploading, setUploading] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);
  const qc = useQueryClient();

  const processFiles = useCallback(
    async (files: { file: File; path: string }[]) => {
      setUploading(true);
      const newResults: typeof results = [];
      // Group files by folder path for collection creation
      const byPath = new Map<string, File[]>();
      for (const { file, path } of files) {
        const existing = byPath.get(path) || [];
        existing.push(file);
        byPath.set(path, existing);
      }

      // Resolve all unique folder paths to collection IDs upfront
      const pathToColId = new Map<string, string>();
      const allPaths = new Set(
        Array.from(byPath.keys()).filter((p) => p.length > 0)
      );
      for (const folderPath of allPaths) {
        const parts = folderPath.split("/");
        let parentId: string | undefined;
        for (let i = 0; i < parts.length; i++) {
          const subPath = parts.slice(0, i + 1).join("/");
          if (pathToColId.has(subPath)) {
            parentId = pathToColId.get(subPath);
          } else {
            const col = await api.collections.getOrCreate(parts[i], parentId);
            pathToColId.set(subPath, col.id);
            parentId = col.id;
          }
        }
      }

      for (const [folderPath, folderFiles] of byPath) {
        const colId = pathToColId.get(folderPath);

        for (const file of folderFiles) {
          try {
            const data = await upload.mutateAsync(file);
            if (colId) {
              await api.collections.addPapers(colId, [data.id]);
            }
            newResults.push({
              file: file.name,
              collection: folderPath || undefined,
              status: "success",
              data,
            });
          } catch (err) {
            newResults.push({
              file: file.name,
              collection: folderPath || undefined,
              status: "error",
              error: err instanceof Error ? err.message : "Upload failed",
            });
          }
        }
      }

      setResults((prev) => [...newResults, ...prev]);
      setUploading(false);
      // Refresh collections if any folders were processed
      const hadFolders = Array.from(byPath.keys()).some((p) => p.length > 0);
      if (hadFolders) {
        qc.invalidateQueries({ queryKey: ["collections"] });
      }
    },
    [upload, qc]
  );

  // Handle native drop to support folders
  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragActive(false);
      if (uploading) return;

      const items = e.dataTransfer.items;
      const allFiles: { file: File; path: string }[] = [];

      if (items) {
        const entries: FileSystemEntry[] = [];
        for (let i = 0; i < items.length; i++) {
          const entry = items[i].webkitGetAsEntry?.();
          if (entry) entries.push(entry);
        }
        for (const entry of entries) {
          allFiles.push(...(await readEntries(entry)));
        }
      }

      if (allFiles.length === 0) {
        // Fallback: regular files
        const files = Array.from(e.dataTransfer.files).filter((f) =>
          f.name.toLowerCase().endsWith(".pdf")
        );
        for (const f of files) allFiles.push({ file: f, path: "" });
      }

      if (allFiles.length > 0) processFiles(allFiles);
    },
    [uploading, processFiles]
  );

  // Also support click-to-browse (files only)
  const inputRef = useRef<HTMLInputElement>(null);
  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []).filter((f) =>
        f.name.toLowerCase().endsWith(".pdf")
      );
      if (files.length > 0) {
        processFiles(files.map((f) => ({ file: f, path: "" })));
      }
      e.target.value = "";
    },
    [processFiles]
  );

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragActive(true); }}
        onDragLeave={() => setIsDragActive(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`flex items-center justify-center rounded-lg border-2 border-dashed py-8 px-6 transition-colors cursor-pointer ${
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/40"
        } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={handleFileInput}
        />
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
            <span>{isDragActive ? "Drop PDFs or folders here" : "Drop PDFs or folders here, or click to browse"}</span>
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
              {r.collection && (
                <span className="text-xs text-muted-foreground shrink-0">
                  {r.collection}
                </span>
              )}
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
      qc.invalidateQueries({ queryKey: ["collection-detail"] });
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
  draggable = true,
}: {
  paper: PaperSummary;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
  draggable?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="border-b border-border last:border-b-0"
      draggable={draggable}
      onDragStart={(e) => {
        e.dataTransfer.setData("application/reflens-papers", JSON.stringify([paper.id]));
        e.dataTransfer.effectAllowed = "move";
      }}
    >
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

// Folder tree node
function FolderNode({
  col,
  depth,
  activeId,
  onSelect,
  onDelete,
  onCreate,
  onDrop,
}: {
  col: PaperCollection;
  depth: number;
  activeId: string | null;
  onSelect: (id: string | null) => void;
  onDelete: (id: string) => void;
  onCreate: (name: string, parentId: string) => void;
  onDrop: (paperIds: string[], colId: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const hasChildren = col.children && col.children.length > 0;

  useEffect(() => {
    if (creating && inputRef.current) inputRef.current.focus();
  }, [creating]);

  return (
    <div>
      <div
        className={`group/folder flex items-center gap-1 py-1 px-1 rounded-md cursor-pointer transition-colors ${
          activeId === col.id
            ? "bg-primary/10 text-primary"
            : dragOver
              ? "bg-primary/5 border border-primary/20"
              : "hover:bg-muted text-muted-foreground hover:text-foreground"
        }`}
        style={{ paddingLeft: `${4 + depth * 16}px` }}
        onClick={() => onSelect(col.id === activeId ? null : col.id)}
        onContextMenu={(e) => {
          e.preventDefault();
          if (confirm(`Delete "${col.name}"? Papers won't be deleted.`)) onDelete(col.id);
        }}
        onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const data = e.dataTransfer.getData("application/reflens-papers");
          if (data) onDrop(JSON.parse(data), col.id);
        }}
      >
        {hasChildren || creating ? (
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="shrink-0 p-0.5"
          >
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </button>
        ) : (
          <span className="w-4" />
        )}
        <FolderOpen className="h-3.5 w-3.5 shrink-0" />
        <span className="text-xs font-medium truncate flex-1">{col.name}</span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            setCreating(true);
            setExpanded(true);
          }}
          className="opacity-0 group-hover/folder:opacity-100 shrink-0 text-muted-foreground hover:text-foreground transition-all"
          title="New sub-collection"
        >
          <Plus className="h-3 w-3" />
        </button>
        <span className="text-xs opacity-50">{col.paper_count}</span>
      </div>
      {expanded && (
        <div>
          {(hasChildren) && col.children.map((child) => (
            <FolderNode
              key={child.id}
              col={child}
              depth={depth + 1}
              activeId={activeId}
              onSelect={onSelect}
              onDelete={onDelete}
              onCreate={onCreate}
              onDrop={onDrop}
            />
          ))}
          {creating && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (newName.trim()) {
                  onCreate(newName.trim(), col.id);
                  setNewName("");
                  setCreating(false);
                }
              }}
              className="flex items-center gap-1 py-1"
              style={{ paddingLeft: `${4 + (depth + 1) * 16}px` }}
            >
              <FolderPlus className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onBlur={() => { if (!newName.trim()) setCreating(false); }}
                onKeyDown={(e) => { if (e.key === "Escape") { setCreating(false); setNewName(""); } }}
                placeholder="Collection name..."
                className="flex-1 text-xs bg-transparent outline-none border-b border-border focus:border-primary"
              />
            </form>
          )}
        </div>
      )}
    </div>
  );
}

function FolderTree({
  collections,
  activeId,
  onSelect,
  onDelete,
  onCreate,
  onDrop,
}: {
  collections: PaperCollection[];
  activeId: string | null;
  onSelect: (id: string | null) => void;
  onDelete: (id: string) => void;
  onCreate: (name: string, parentId?: string) => void;
  onDrop: (paperIds: string[], colId: string) => void;
}) {
  const [creatingRoot, setCreatingRoot] = useState(false);
  const [rootName, setRootName] = useState("");
  const rootInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (creatingRoot && rootInputRef.current) rootInputRef.current.focus();
  }, [creatingRoot]);

  return (
    <div className="space-y-0.5">
      <button
        onClick={() => onSelect(null)}
        className={`flex items-center gap-1.5 w-full py-1 px-2 rounded-md text-xs font-medium transition-colors ${
          !activeId
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-muted"
        }`}
      >
        <FolderOpen className="h-3.5 w-3.5" />
        All papers
      </button>
      {collections.map((col) => (
        <FolderNode
          key={col.id}
          col={col}
          depth={0}
          activeId={activeId}
          onSelect={onSelect}
          onDelete={onDelete}
          onCreate={(name, parentId) => onCreate(name, parentId)}
          onDrop={onDrop}
        />
      ))}
      {creatingRoot ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (rootName.trim()) {
              onCreate(rootName.trim());
              setRootName("");
              setCreatingRoot(false);
            }
          }}
          className="flex items-center gap-1 py-1 px-2"
        >
          <FolderPlus className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <input
            ref={rootInputRef}
            type="text"
            value={rootName}
            onChange={(e) => setRootName(e.target.value)}
            onBlur={() => { if (!rootName.trim()) setCreatingRoot(false); }}
            onKeyDown={(e) => { if (e.key === "Escape") { setCreatingRoot(false); setRootName(""); } }}
            placeholder="Collection name..."
            className="flex-1 text-xs bg-transparent outline-none border-b border-border focus:border-primary"
          />
        </form>
      ) : (
        <button
          onClick={() => setCreatingRoot(true)}
          className="flex items-center gap-1.5 w-full py-1 px-2 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          New collection
        </button>
      )}
    </div>
  );
}

export default function LibraryPage() {
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedTags, setSelectedTags] = useState<Tag[]>([]);
  const [activeCollection, setActiveCollection] = useState<string | null>(null);
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
  const { data: collectionsData } = useQuery({
    queryKey: ["collections"],
    queryFn: () => api.collections.list(),
  });
  const { data: collectionDetail } = useQuery({
    queryKey: ["collection-detail", activeCollection],
    queryFn: () => api.collections.get(activeCollection!),
    enabled: !!activeCollection,
  });

  const { data: grobidHealth } = useQuery({
    queryKey: ["grobid-health"],
    queryFn: () => api.grobidHealth(),
    refetchInterval: 30000,
  });
  const grobidDown = grobidHealth?.status === "down";

  const deleteCollectionMutation = useMutation({
    mutationFn: (id: string) => api.collections.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["collections"] });
      if (activeCollection) setActiveCollection(null);
    },
  });

  const { data: aiInfo } = useQuery({
    queryKey: ["ai-info"],
    queryFn: () => api.aiInfo(),
  });
  const availableModels = aiInfo?.models ?? [];
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  useEffect(() => {
    if (aiInfo?.default && !selectedModelId) setSelectedModelId(aiInfo.default);
  }, [aiInfo, selectedModelId]);

  const deleteMutation = useDeletePaper();
  const summarizeAll = useBulkAction("summarize-all");
  const tagAll = useBulkAction("tag-all");

  const collections = collectionsData?.collections ?? [];

  // Determine which papers to show
  const isSearching = searchQuery.length > 0;
  const isCollectionFiltering = !!activeCollection;
  const displayPapers: PaperSummary[] = isSearching
    ? (searchData?.results.map((r) => r.paper) ?? [])
    : isCollectionFiltering
      ? (collectionDetail?.papers ?? [])
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
                setActiveCollection(null);
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

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* GROBID warning */}
        {grobidDown && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 flex items-center gap-2">
            <span className="text-amber-500 text-lg">&#9888;</span>
            <span>
              <strong>GROBID is not running.</strong> PDF extraction will use basic fallback (limited metadata).
            </span>
          </div>
        )}

        {/* Upload */}
        <UploadZone />

        <div className="flex gap-6">
          {/* Folder tree sidebar */}
          {collections.length > 0 && !isSearching && (
            <div className="w-56 shrink-0">
              <FolderTree
                collections={collections}
                activeId={activeCollection}
                onSelect={(id) => {
                  setActiveCollection(id);
                  setSelectedTags([]);
                  setOffset(0);
                }}
                onDelete={(id) => deleteCollectionMutation.mutate(id)}
                onCreate={async (name, parentId) => {
                  await api.collections.create(name, parentId);
                  qc.invalidateQueries({ queryKey: ["collections"] });
                }}
                onDrop={async (paperIds, targetColId) => {
                  // Move: add to target, remove from source if viewing a collection
                  await api.collections.addPapers(targetColId, paperIds);
                  if (activeCollection && activeCollection !== targetColId) {
                    await api.collections.removePapers(activeCollection, paperIds);
                  }
                  qc.invalidateQueries({ queryKey: ["collections"] });
                  qc.invalidateQueries({ queryKey: ["collection-detail"] });
                }}
              />
            </div>
          )}

          {/* Main content */}
          <div className="flex-1 min-w-0 space-y-4">
            {/* Tag selector */}
            {tagsData && tagsData.tags.length > 0 && !isSearching && !isCollectionFiltering && (
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
                    : `${isSearching ? (searchData?.results.length ?? 0) : isCollectionFiltering ? (collectionDetail?.papers.length ?? 0) : (papersData?.total ?? 0)} papers`}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <CollectionActions selectedIds={selectedIds} collections={collections} />

                {selectedIds.size > 0 && (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => summarizeAll.trigger(selectedModelId ?? undefined)}
                      disabled={summarizeAll.isPending || summarizeAll.isActive}
                      className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 transition-colors"
                    >
                      <Sparkles className="h-3 w-3" />
                      Summarize
                    </button>
                    {availableModels.length > 1 && (
                      <select
                        value={selectedModelId ?? ""}
                        onChange={(e) => setSelectedModelId(e.target.value)}
                        className="rounded-full border border-border bg-white px-2 py-1 text-xs text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        {availableModels.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.model} ({m.local ? "local" : m.provider})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
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
                  : isCollectionFiltering
                    ? "No papers in this collection yet. Drag papers here."
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

            {/* Pagination */}
            {!isSearching && !isCollectionFiltering && papersData && (
              <Pagination
                total={papersData.total}
                limit={papersData.limit}
                offset={offset}
                onPageChange={setOffset}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
