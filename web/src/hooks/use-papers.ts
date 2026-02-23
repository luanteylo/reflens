"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function usePapers(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["papers", limit, offset],
    queryFn: () => api.papers.list(limit, offset),
  });
}

export function useDeletePaper() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.papers.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["papers"] }),
  });
}
