"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useTaskContext } from "@/contexts/task-context";
import { useTaskPolling } from "@/hooks/use-task";

export function usePapers(limit = 50, offset = 0, tagIds?: string[]) {
  return useQuery({
    queryKey: ["papers", limit, offset, tagIds],
    queryFn: () => api.papers.list(limit, offset, tagIds),
  });
}

export function useDeletePaper() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.papers.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["collections"] });
      qc.invalidateQueries({ queryKey: ["collection-detail"] });
    },
  });
}

export function useBulkAction(kind: "summarize-all" | "tag-all") {
  const { getTaskId, setTask, clearTask } = useTaskContext();
  const taskId = getTaskId(kind);
  const taskStatus = useTaskPolling(taskId);

  const mutation = useMutation({
    mutationFn: (modelId?: string) =>
      kind === "summarize-all"
        ? api.papers.summarizeAll(modelId)
        : api.papers.tagAll(modelId),
    onSuccess: (data) => {
      setTask(kind, data.task_id);
    },
  });

  const dismiss = () => clearTask(kind);

  const isActive =
    !!taskId &&
    taskStatus.data?.status !== "completed" &&
    taskStatus.data?.status !== "failed";

  const isStarting = !!taskId && !taskStatus.data && taskStatus.isLoading;

  return {
    trigger: (modelId?: string) => mutation.mutate(modelId),
    isPending: mutation.isPending,
    taskId,
    status: taskStatus.data,
    isActive,
    isStarting,
    isComplete: taskStatus.data?.status === "completed",
    isFailed: taskStatus.data?.status === "failed",
    dismiss,
  };
}
