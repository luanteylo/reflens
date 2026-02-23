import { Loader2 } from "lucide-react";

export function LoadingSpinner({ className }: { className?: string }) {
  return <Loader2 className={`animate-spin text-muted-foreground ${className ?? "h-6 w-6"}`} />;
}
