"use client";

import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { TaskStatusResponse } from "@/lib/types";

export function useTaskPolling(taskId: string | null) {
  const qc = useQueryClient();
  const prevCompleted = useRef(0);

  const query = useQuery<TaskStatusResponse>({
    queryKey: ["task", taskId],
    queryFn: () => api.tasks.status(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 1000;
    },
  });

  // Invalidate papers whenever completed count changes
  useEffect(() => {
    if (query.data && query.data.completed > prevCompleted.current) {
      prevCompleted.current = query.data.completed;
      qc.invalidateQueries({ queryKey: ["papers"] });
    }
  }, [query.data, qc]);

  // Reset counter when taskId changes
  useEffect(() => {
    prevCompleted.current = 0;
  }, [taskId]);

  return query;
}
