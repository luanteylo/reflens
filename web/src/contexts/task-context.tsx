"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface TaskState {
  activeTasks: Record<string, string>; // kind -> taskId
  setTask: (kind: string, taskId: string) => void;
  clearTask: (kind: string) => void;
  getTaskId: (kind: string) => string | null;
}

const TaskContext = createContext<TaskState | null>(null);

export function TaskProvider({ children }: { children: ReactNode }) {
  const [activeTasks, setActiveTasks] = useState<Record<string, string>>({});

  const setTask = useCallback((kind: string, taskId: string) => {
    setActiveTasks((prev) => ({ ...prev, [kind]: taskId }));
  }, []);

  const clearTask = useCallback((kind: string) => {
    setActiveTasks((prev) => {
      const next = { ...prev };
      delete next[kind];
      return next;
    });
  }, []);

  const getTaskId = useCallback(
    (kind: string) => activeTasks[kind] ?? null,
    [activeTasks]
  );

  return (
    <TaskContext.Provider value={{ activeTasks, setTask, clearTask, getTaskId }}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTaskContext() {
  const ctx = useContext(TaskContext);
  if (!ctx) throw new Error("useTaskContext must be used within TaskProvider");
  return ctx;
}
