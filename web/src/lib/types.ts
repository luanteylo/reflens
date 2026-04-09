export interface Author {
  id: string;
  name: string;
  affiliations: string[] | null;
}

export interface Tag {
  id: string;
  name: string;
  parent_id: string | null;
}

export interface PaperTag {
  id: string;
  tag_id: string;
  tag_name: string;
  section: string | null;
  confidence: number;
  source: string;
}

export interface Citation {
  id: string;
  cited_title: string;
  cited_authors: string | null;
  cited_year: number | null;
  cited_doi: string | null;
  cited_paper_id: string | null;
  raw_reference: string | null;
}

export interface UserNote {
  id: string;
  content: string | null;
  reading_status: string;
  relevance_score: number | null;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaperSummary {
  id: string;
  title: string;
  abstract: string | null;
  year: number | null;
  doi: string | null;
  ai_summary: string | null;
  created_at: string;
  authors: Author[];
  tags: PaperTag[];
}

export interface PaperDetail extends PaperSummary {
  full_text: string | null;
  sections: Record<string, string> | null;
  source_file: string | null;
  ai_key_contributions: string[] | null;
  ai_methodology: string | null;
  ai_findings: string | null;
  ai_limitations: string | null;
  updated_at: string;
  citations: Citation[];
  notes: UserNote[];
}

export interface PaperListResponse {
  papers: PaperSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaperUploadResponse {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  citations_count: number;
}

export interface SummarizeResponse {
  id: string;
  ai_summary: string | null;
  ai_key_contributions: string[] | null;
  ai_methodology: string | null;
  ai_findings: string | null;
  ai_limitations: string | null;
}

export interface TagGenerateResponse {
  id: string;
  tags: string[];
}

export interface BulkActionResponse {
  done: string[];
  failed: string[];
}

export interface SearchResultItem {
  paper: PaperSummary;
  score: number | null;
}

export interface SearchResponse {
  results: SearchResultItem[];
  query: string;
}

export interface ReferencesRequest {
  text: string;
  limit?: number;
  explain?: boolean;
  tag_ids?: string[];
  collection_ids?: string[];
  model_id?: string;
}

export interface PaperCollection {
  id: string;
  name: string;
  parent_id: string | null;
  paper_count: number;
  children: PaperCollection[];
  created_at: string;
}

export interface CollectionListResponse {
  collections: PaperCollection[];
}

export interface CollectionDetailResponse extends PaperCollection {
  papers: PaperSummary[];
}

export interface SavedSearch {
  id: string;
  text: string;
  collection_id: string | null;
  collection_name: string | null;
  results: ReferenceResult[] | null;
  created_at: string;
}

export interface SavedSearchListResponse {
  searches: SavedSearch[];
}

export interface ReferenceResult {
  paper: PaperSummary;
  score: number;
  explanation: string | null;
  stance: "supports" | "contradicts" | "neutral" | null;
}

export interface ReferencesResponse {
  results: ReferenceResult[];
  text: string;
}

export interface AuthorListResponse {
  authors: Author[];
  total: number;
  limit: number;
  offset: number;
}

export interface TagListResponse {
  tags: Tag[];
}

export interface TagPapersResponse {
  tag: Tag;
  papers: PaperSummary[];
}

export interface NoteUpdateRequest {
  content?: string | null;
  reading_status?: string;
  relevance_score?: number | null;
  is_favorite?: boolean;
}

export interface TaskCreatedResponse {
  task_id: string;
}

export interface TaskStatusResponse {
  id: string;
  kind: string;
  status: "pending" | "running" | "completed" | "failed";
  total: number;
  completed: number;
  failed: number;
  done_titles: string[];
  failed_titles: string[];
  error: string | null;
}
