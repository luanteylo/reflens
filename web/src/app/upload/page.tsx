"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { CheckCircle2, FileUp, Upload, XCircle } from "lucide-react";
import { useUpload } from "@/hooks/use-upload";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import type { PaperUploadResponse } from "@/lib/types";

interface UploadResult {
  file: string;
  status: "success" | "error";
  data?: PaperUploadResponse;
  error?: string;
}

export default function UploadPage() {
  const router = useRouter();
  const upload = useUpload();
  const [results, setResults] = useState<UploadResult[]>([]);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploading(true);
      const newResults: UploadResult[] = [];
      for (const file of acceptedFiles) {
        try {
          const data = await upload.mutateAsync(file);
          newResults.push({ file: file.name, status: "success", data });
        } catch (err) {
          newResults.push({
            file: file.name,
            status: "error",
            error: err instanceof Error ? err.message : "Upload failed",
          });
        }
      }
      setResults((prev) => [...newResults, ...prev]);
      setUploading(false);
    },
    [upload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    disabled: uploading,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Upload Papers</h1>

      <div
        {...getRootProps()}
        className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors cursor-pointer ${
          isDragActive
            ? "border-primary bg-accent"
            : "border-border hover:border-primary/50 hover:bg-muted/50"
        } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <>
            <LoadingSpinner className="h-10 w-10 mb-4" />
            <p className="text-lg font-medium">Uploading...</p>
          </>
        ) : (
          <>
            {isDragActive ? (
              <FileUp className="h-10 w-10 mb-4 text-primary" />
            ) : (
              <Upload className="h-10 w-10 mb-4 text-muted-foreground" />
            )}
            <p className="text-lg font-medium">
              {isDragActive ? "Drop PDFs here" : "Drag & drop PDFs here"}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              or click to browse files
            </p>
          </>
        )}
      </div>

      {results.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Results</h2>
          {results.map((r, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-lg border border-border p-4"
            >
              {r.status === "success" ? (
                <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />
              ) : (
                <XCircle className="h-5 w-5 text-destructive shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                {r.status === "success" && r.data ? (
                  <>
                    <button
                      onClick={() => router.push(`/papers/${r.data!.id}`)}
                      className="font-medium text-primary hover:underline text-left"
                    >
                      {r.data.title}
                    </button>
                    <p className="text-xs text-muted-foreground">
                      {r.data.authors.join(", ")}
                      {r.data.year ? ` (${r.data.year})` : ""}
                      {" -- "}
                      {r.data.citations_count} citations extracted
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-medium">{r.file}</p>
                    <p className="text-xs text-destructive">{r.error}</p>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
