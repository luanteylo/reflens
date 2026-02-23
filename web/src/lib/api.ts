import type {
  AuthorListResponse,
  NoteUpdateRequest,
  PaperDetail,
  PaperListResponse,
  PaperSummary,
  PaperUploadResponse,
  ReferencesRequest,
  ReferencesResponse,
  SearchResponse,
  SummarizeResponse,
  TagGenerateResponse,
  TagListResponse,
  TagPapersResponse,
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
    list(limit = 50, offset = 0) {
      return request<PaperListResponse>(`/papers?limit=${limit}&offset=${offset}`);
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
    updateNotes(id: string, body: NoteUpdateRequest) {
      return request<UserNote>(`/papers/${id}/notes`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    },
  },
  search(q: string) {
    return request<SearchResponse>(`/search?q=${encodeURIComponent(q)}`);
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
  authors: {
    list(limit = 50, offset = 0) {
      return request<AuthorListResponse>(`/authors?limit=${limit}&offset=${offset}`);
    },
    papers(authorId: string) {
      return request<PaperSummary[]>(`/authors/${authorId}/papers`);
    },
  },
};
