import type {
  AISummaryResponse,
  AuthorListResponse,
  CollectionDetailResponse,
  CollectionListResponse,
  NoteUpdateRequest,
  PaperCollection,
  PaperDetail,
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

let _refreshing: Promise<void> | null = null;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
  });

  // Auto-refresh on 401 (expired access token)
  if (res.status === 401 && !path.includes("/auth/")) {
    if (!_refreshing) {
      _refreshing = fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      }).then((r) => {
        if (!r.ok) {
          // Refresh failed — redirect to login
          if (typeof window !== "undefined") window.location.href = "/login";
        }
      }).finally(() => { _refreshing = null; });
    }
    await _refreshing;
    // Retry the original request
    res = await fetch(`${BASE}${path}`, {
      ...init,
      credentials: "include",
    });
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface AuthUser {
  user_id: string;
  email: string;
  plan: string;
  email_verified: boolean;
  created_at: string | null;
}

// Papers
export const api = {
  auth: {
    signup(email: string, password: string) {
      return request<{ message: string }>("/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    },
    login(email: string, password: string) {
      return request<AuthUser>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    },
    logout() {
      return request<{ message: string }>("/auth/logout", { method: "POST" });
    },
    refresh() {
      return request<{ message: string }>("/auth/refresh", { method: "POST" });
    },
    me() {
      return request<AuthUser>("/auth/me");
    },
    verifyEmail(token: string) {
      return request<{ message: string }>("/auth/verify-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
    },
    changePassword(currentPassword: string, newPassword: string) {
      return request<{ message: string }>("/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
    },
    deleteAccount(password: string) {
      return request<{ message: string }>("/auth/account", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
    },
  },
  apiKeys: {
    list() {
      return request<{ id: string; provider: string; label: string; key_hint: string; created_at: string }[]>("/api-keys");
    },
    add(provider: string, apiKey: string, label?: string) {
      return request<{ id: string; provider: string; label: string }>("/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: apiKey, label: label ?? provider }),
      });
    },
    delete(id: string) {
      return request<void>(`/api-keys/${id}`, { method: "DELETE" });
    },
  },
  stats() {
    return request<{ papers: number; collections: number; storage_bytes: number; storage_mb: number }>("/health/stats");
  },
  usage() {
    return request<{
      total_prompt_tokens: number;
      total_completion_tokens: number;
      total_tokens: number;
      total_cost_usd: number;
      total_requests: number;
      by_model: { provider: string; model: string; prompt_tokens: number; completion_tokens: number; cost_usd: number; requests: number }[];
    }>("/health/usage");
  },
  preferences: {
    get() {
      return request<{ default_model: string | null; search_limit: number; explain_by_default: boolean; context_length: number }>("/preferences");
    },
    update(prefs: Partial<{ default_model: string | null; search_limit: number; explain_by_default: boolean; context_length: number }>) {
      return request<{ default_model: string | null; search_limit: number; explain_by_default: boolean; context_length: number }>("/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      });
    },
  },
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
    summarize(id: string, modelId?: string, userPrompt?: string) {
      return request<AISummaryResponse>(`/papers/${id}/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId ?? null, user_prompt: userPrompt ?? null }),
      });
    },
    summaries(id: string) {
      return request<AISummaryResponse[]>(`/papers/${id}/summaries`);
    },
    deleteSummary(paperId: string, summaryId: string) {
      return request<void>(`/papers/${paperId}/summaries/${summaryId}`, { method: "DELETE" });
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
    cite(id: string) {
      return request<{ short: string; full: string; bibtex: string }>(`/papers/${id}/cite`);
    },
    updateNotes(id: string, body: NoteUpdateRequest) {
      return request<UserNote>(`/papers/${id}/notes`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    },
    summarizeAll(modelId?: string, paperIds?: string[], userPrompt?: string) {
      return request<TaskCreatedResponse>("/papers/summarize-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId ?? null, paper_ids: paperIds ?? null, user_prompt: userPrompt ?? null }),
      });
    },
    tagAll(modelId?: string, paperIds?: string[]) {
      return request<TaskCreatedResponse>("/papers/tag-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId ?? null, paper_ids: paperIds ?? null }),
      });
    },
  },
  tasks: {
    status(taskId: string) {
      return request<TaskStatusResponse>(`/tasks/${taskId}`);
    },
  },
  search(q: string, collectionIds?: string[]) {
    const params = new URLSearchParams({ q });
    if (collectionIds) {
      for (const id of collectionIds) params.append("collection_ids", id);
    }
    return request<SearchResponse>(`/search?${params.toString()}`);
  },
  explainSingle(query: string, paperId: string, modelId?: string) {
    return request<{ stance: string; explanation: string }>("/search/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, paper_id: paperId, model_id: modelId ?? null }),
    });
  },
  findReferences(body: ReferencesRequest, signal?: AbortSignal) {
    return request<ReferencesResponse>("/search/references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
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
  collections: {
    list() {
      return request<CollectionListResponse>("/collections");
    },
    get(id: string) {
      return request<CollectionDetailResponse>(`/collections/${id}`);
    },
    create(name: string, parentId?: string) {
      return request<PaperCollection>("/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, parent_id: parentId ?? null }),
      });
    },
    getOrCreate(name: string, parentId?: string) {
      return request<PaperCollection>("/collections/get-or-create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, parent_id: parentId ?? null }),
      });
    },
    delete(id: string) {
      return request<void>(`/collections/${id}`, { method: "DELETE" });
    },
    addPapers(colId: string, paperIds: string[]) {
      return request<void>(`/collections/${colId}/papers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_ids: paperIds }),
      });
    },
    removePapers(colId: string, paperIds: string[]) {
      return request<void>(`/collections/${colId}/papers`, {
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
    save(text: string, collectionIds?: string[], results?: unknown[]) {
      return request<SavedSearch>("/saved-searches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          collection_id: collectionIds?.[0] ?? null,
          results: results ?? null,
        }),
      });
    },
    delete(id: string) {
      return request<void>(`/saved-searches/${id}`, { method: "DELETE" });
    },
  },
  aiInfo() {
    return request<{
      provider: string;
      model: string;
      default: string;
      models: { id: string; provider: string; model: string; local: boolean }[];
    }>("/health/ai");
  },
  grobidHealth() {
    return request<{ status: string }>("/health/grobid");
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
