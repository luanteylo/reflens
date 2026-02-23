"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.papers.upload(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["papers"] }),
  });
}
