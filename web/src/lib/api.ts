import type {
  AuthorListResponse,
  GroupDetailResponse,
  GroupListResponse,
  NoteUpdateRequest,
  PaperDetail,
  PaperGroup,
  PaperListResponse,
  PaperSummary,
  PaperUploadResponse,
  ReferencesRequest,
  ReferencesResponse,
  SavedSearch,
  SavedSearchListResponse,
  SearchResponse,
  SummarizeResponse,
  TagGenerateResponse,
  TagListResponse,
  TagPapersResponse,
  TaskCreatedResponse,
  TaskStatusResponse,
  UserNote,
} from "./types";

function getBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000/api/v1`;
  }
  return "http://localhost:8000/api/v1";
}

const BASE = getBaseUrl();

export function getPdfUrl(paperId: string): string {
  return `${BASE}/papers/${paperId}/pdf`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Papers
export const api = {
  papers: {
    list(limit = 50, offset = 0, tagIds?: string[]) {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(offset));
      if (tagIds) {
        for (const id of tagIds) params.append("tag_ids", id);
      }
      return request<PaperListResponse>(`/papers?${params.toString()}`);
    },
    get(id: string) {
      return request<PaperDetail>(`/papers/${id}`);
    },
    delete(id: string) {
      return request<void>(`/papers/${id}`, { method: "DELETE" });
    },
    upload(file: File) {
      const form = new FormData();
      form.append("file", file);
      return request<PaperUploadResponse>("/papers/upload", {
        method: "POST",
        body: form,
      });
    },
    summarize(id: string) {
      return request<SummarizeResponse>(`/papers/${id}/summarize`, { method: "POST" });
    },
    tag(id: string) {
      return request<TagGenerateResponse>(`/papers/${id}/tag`, { method: "POST" });
    },
    citations(id: string) {
      return request<PaperDetail["citations"]>(`/papers/${id}/citations`);
    },
    update(id: string, data: { doi?: string; year?: number; title?: string }) {
      return request<PaperSummary>(`/papers/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
    },
    async bibtex(id: string): Promise<string> {
      const res = await fetch(`${BASE}/papers/${id}/bibtex`);
      if (!res.ok) throw new Error(`API ${res.status}`);
      return res.text();
    },
    updateNotes(id: string, body: NoteUpdateRequest) {
      return request<UserNote>(`/papers/${id}/notes`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    },
    summarizeAll() {
      return request<TaskCreatedResponse>("/papers/summarize-all", { method: "POST" });
    },
    tagAll() {
      return request<TaskCreatedResponse>("/papers/tag-all", { method: "POST" });
    },
  },
  tasks: {
    status(taskId: string) {
      return request<TaskStatusResponse>(`/tasks/${taskId}`);
    },
  },
  search(q: string, groupId?: string) {
    const params = new URLSearchParams({ q });
    if (groupId) params.set("group_id", groupId);
    return request<SearchResponse>(`/search?${params.toString()}`);
  },
  findReferences(body: ReferencesRequest) {
    return request<ReferencesResponse>("/search/references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
  tags: {
    list() {
      return request<TagListResponse>("/tags");
    },
    papers(tagId: string) {
      return request<TagPapersResponse>(`/tags/${tagId}/papers`);
    },
  },
  groups: {
    list() {
      return request<GroupListResponse>("/groups");
    },
    get(id: string) {
      return request<GroupDetailResponse>(`/groups/${id}`);
    },
    create(name: string) {
      return request<PaperGroup>("/groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
    },
    delete(id: string) {
      return request<void>(`/groups/${id}`, { method: "DELETE" });
    },
    addPapers(groupId: string, paperIds: string[]) {
      return request<void>(`/groups/${groupId}/papers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_ids: paperIds }),
      });
    },
    removePapers(groupId: string, paperIds: string[]) {
      return request<void>(`/groups/${groupId}/papers`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_ids: paperIds }),
      });
    },
  },
  savedSearches: {
    list() {
      return request<SavedSearchListResponse>("/saved-searches");
    },
    save(text: string, groupId?: string, results?: unknown[]) {
      return request<SavedSearch>("/saved-searches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          group_id: groupId ?? null,
          results: results ?? null,
        }),
      });
    },
    delete(id: string) {
      return request<void>(`/saved-searches/${id}`, { method: "DELETE" });
    },
  },
  authors: {
    list(limit = 50, offset = 0) {
      return request<AuthorListResponse>(`/authors?limit=${limit}&offset=${offset}`);
    },
    papers(authorId: string) {
      return request<PaperSummary[]>(`/authors/${authorId}/papers`);
    },
  },
};
