"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, force = false }: { file: File; force?: boolean }) =>
      api.papers.upload(file, force),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["papers"] }),
  });
}
