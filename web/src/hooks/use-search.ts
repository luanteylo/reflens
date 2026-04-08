"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ReferencesRequest } from "@/lib/types";

export function useSearch(query: string, collectionIds?: string[]) {
  return useQuery({
    queryKey: ["search", query, collectionIds],
    queryFn: () => api.search(query, collectionIds),
    enabled: query.length > 0,
  });
}

export function useFindReferences() {
  return useMutation({
    mutationFn: (body: ReferencesRequest) => api.findReferences(body),
  });
}
