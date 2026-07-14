"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowsClockwise, Trash } from "@phosphor-icons/react/ssr";
import { useAuth } from "@/lib/auth-context";
import { apiDelete, apiGet } from "@/lib/api";
import type { TemplateManifestEntry } from "@/lib/document-template";
import PageHeader from "../page-header";

type DocumentSummary = {
  id: number;
  template_id: string;
  status: "in_progress" | "completed";
  updated_at: string;
};

export default function DocumentList({ templates }: { templates: TemplateManifestEntry[] }) {
  const { status: authStatus } = useAuth();
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authStatus !== "authenticated") return;
    let cancelled = false;
    apiGet<DocumentSummary[]>("/api/documents")
      .then((docs) => {
        if (!cancelled) setDocuments(docs);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load your documents. Please refresh to try again.");
      });
    return () => {
      cancelled = true;
    };
  }, [authStatus]);

  const templateById = new Map(templates.map((t) => [t.id, t]));

  const handleDelete = async (id: number) => {
    try {
      await apiDelete(`/api/documents/${id}`);
      setDocuments((prev) => (prev ? prev.filter((doc) => doc.id !== id) : prev));
    } catch {
      setError("Couldn't delete that document. Please try again.");
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-6 py-10 sm:px-10">
      <PageHeader
        title="My Documents"
        subtitle="Resume an in-progress document or start a new one from the document list."
        backLink={{ href: "/", label: "Back to documents" }}
      />

      {authStatus === "guest" && (
        <div className="flex flex-col items-start gap-3 rounded-xl border border-border bg-card p-6 shadow-sm sm:p-7">
          <p className="text-sm text-muted-foreground">
            Log in to see your saved documents.
          </p>
          <div className="flex gap-3">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary-hover"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground shadow-sm transition-colors duration-200 hover:bg-muted"
            >
              Sign up
            </Link>
          </div>
        </div>
      )}

      {authStatus === "loading" && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <ArrowsClockwise size={16} weight="bold" className="animate-spin" />
          Loading…
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}

      {authStatus === "authenticated" && documents !== null && (
        documents.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            You don&apos;t have any saved documents yet.{" "}
            <Link href="/" className="font-medium text-primary hover:text-primary-hover">
              Start one
            </Link>
            .
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {documents.map((doc) => {
              const template = templateById.get(doc.template_id);
              return (
                <div
                  key={doc.id}
                  className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-serif text-lg font-semibold text-foreground">
                      {template?.title ?? doc.template_id}
                    </span>
                    <button
                      type="button"
                      onClick={() => void handleDelete(doc.id)}
                      aria-label="Delete document"
                      className="cursor-pointer text-muted-foreground transition-colors duration-200 hover:text-destructive"
                    >
                      <Trash size={18} weight="bold" />
                    </button>
                  </div>
                  <span
                    className={`w-fit rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      doc.status === "completed"
                        ? "bg-primary/10 text-primary"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {doc.status === "completed" ? "Ready to download" : "In progress"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    Updated {new Date(doc.updated_at + "Z").toLocaleString()}
                  </span>
                  <Link
                    href={`/documents/${doc.template_id}/?doc=${doc.id}`}
                    className="mt-2 inline-flex w-fit items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary-hover"
                  >
                    Resume
                  </Link>
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}
