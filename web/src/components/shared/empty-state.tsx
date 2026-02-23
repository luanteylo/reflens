import { FileQuestion } from "lucide-react";

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <FileQuestion className="h-12 w-12 mb-4" />
      <p className="text-lg">{message}</p>
    </div>
  );
}
