"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { NoteUpdateRequest } from "@/lib/types";

export function usePaper(id: string) {
  return useQuery({
    queryKey: ["paper", id],
    queryFn: () => api.papers.get(id),
    enabled: !!id,
  });
}

export function useSummarize(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.papers.summarize(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["paper", id] }),
  });
}

export function useGenerateTags(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.papers.tag(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["paper", id] }),
  });
}

export function useUpdateNotes(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: NoteUpdateRequest) => api.papers.updateNotes(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["paper", id] }),
  });
}
