"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ReferencesRequest } from "@/lib/types";

export function useSearch(query: string, groupId?: string) {
  return useQuery({
    queryKey: ["search", query, groupId],
    queryFn: () => api.search(query, groupId),
    enabled: query.length > 0,
  });
}

export function useFindReferences() {
  return useMutation({
    mutationFn: (body: ReferencesRequest) => api.findReferences(body),
  });
}
