"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowsClockwise,
  DownloadSimple,
  FileText,
  PaperPlaneTilt,
} from "@phosphor-icons/react/ssr";
import { fillTemplateBody, type Template, type TemplateManifestEntry } from "@/lib/document-template";
import { apiGet, apiPost, apiPut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import PageHeader from "@/app/page-header";

type FieldValues = Record<string, string>;
type ChatRole = "user" | "assistant";
type ChatMessage = { role: ChatRole; content: string };
type ChatApiResponse = {
  reply: string;
  fields: Record<string, string | null>;
  suggested_template_id?: string | null;
};
type PersistedDocument = {
  id: number;
  template_id: string;
  status: "in_progress" | "completed";
  updated_at: string;
  fields: Record<string, string | null>;
  messages: ChatMessage[];
};

function emptyFieldValues(template: Template): FieldValues {
  return Object.fromEntries(template.fields.map((field) => [field.key, ""]));
}

function nullableToFieldValues(fields: Record<string, string | null>): FieldValues {
  return Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, value ?? ""]));
}

export default function DocumentCreator({
  template,
  templates,
}: {
  template: Template;
  templates: TemplateManifestEntry[];
}) {
  const { status: authStatus } = useAuth();
  const docParam = useSearchParams().get("doc");

  const [values, setValues] = useState<FieldValues>(() => emptyFieldValues(template));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documentId, setDocumentId] = useState<number | null>(null);
  const [suggestedTemplateId, setSuggestedTemplateId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveFailed, setSaveFailed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (authStatus === "loading") return;
    let cancelled = false;

    const applyDocument = (doc: PersistedDocument) => {
      if (cancelled) return;
      setMessages(doc.messages);
      setValues(nullableToFieldValues(doc.fields));
      setDocumentId(doc.id);
    };

    const loadGuestGreeting = async (notice?: string) => {
      try {
        const data = await apiGet<ChatApiResponse>(`/api/chat/${template.id}/greeting`);
        if (cancelled) return;
        setMessages([{ role: "assistant", content: data.reply }]);
        setValues(nullableToFieldValues(data.fields));
        setDocumentId(null);
        if (notice) setError(notice);
      } catch {
        if (cancelled) return;
        setError("Couldn't reach the assistant. Please refresh the page to try again.");
      }
    };

    (async () => {
      if (docParam) {
        try {
          applyDocument(await apiGet<PersistedDocument>(`/api/documents/${docParam}`));
        } catch {
          if (!cancelled) await loadGuestGreeting("Couldn't load that saved document - starting fresh.");
        }
        return;
      }

      if (authStatus === "authenticated") {
        try {
          applyDocument(await apiPost<PersistedDocument>("/api/documents", { template_id: template.id }));
        } catch {
          if (!cancelled) await loadGuestGreeting();
        }
        return;
      }

      await loadGuestGreeting();
    })();

    return () => {
      cancelled = true;
    };
  }, [template.id, authStatus, docParam]);

  useEffect(() => {
    const container = threadRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Runs after React commits the re-enabled (non-disabled) input, so the
  // focus call can't race ahead of the DOM update the way it would inline
  // in sendMessage's `finally` block.
  useEffect(() => {
    if (!isSending) inputRef.current?.focus();
  }, [isSending]);

  const missingRequiredFields = useMemo(
    () => template.fields.filter((field) => field.required && !values[field.key]?.trim()),
    [values, template.fields]
  );

  const filledBody = useMemo(
    () => fillTemplateBody(template.body, values, template.fields),
    [values, template.body, template.fields]
  );

  const suggestedTemplate = suggestedTemplateId
    ? templates.find((t) => t.id === suggestedTemplateId)
    : null;

  const sendMessage = async (content: string) => {
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setIsSending(true);
    setError(null);
    setSaveFailed(false);
    try {
      const data = await apiPost<ChatApiResponse>(`/api/chat/${template.id}/message`, {
        messages: nextMessages,
        fields: values,
      });
      const updatedFields = nullableToFieldValues(data.fields);
      const updatedMessages: ChatMessage[] = [...nextMessages, { role: "assistant", content: data.reply }];
      setMessages(updatedMessages);
      setValues(updatedFields);
      setSuggestedTemplateId(data.suggested_template_id ?? null);
      if (documentId !== null) {
        try {
          await apiPut(`/api/documents/${documentId}`, { fields: updatedFields, messages: updatedMessages });
        } catch {
          setSaveFailed(true);
        }
      }
    } catch {
      setError("Something went wrong sending that message. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;
    setInput("");
    void sendMessage(trimmed);
  };

  const handleDownload = async () => {
    setIsGeneratingPdf(true);
    try {
      const { jsPDF } = await import("jspdf");
      const doc = new jsPDF({ unit: "pt", format: "letter" });

      const marginX = 56;
      const marginY = 56;
      const lineHeight = 16;
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const maxWidth = pageWidth - marginX * 2;

      doc.setFont("times", "normal");
      doc.setFontSize(11);

      const lines: string[] = doc.splitTextToSize(filledBody, maxWidth);
      let cursorY = marginY;

      for (const line of lines) {
        if (cursorY > pageHeight - marginY) {
          doc.addPage();
          cursorY = marginY;
        }
        doc.text(line, marginX, cursorY);
        cursorY += lineHeight;
      }

      doc.save(`${template.id}.pdf`);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-10 sm:px-10">
      <PageHeader
        title={template.title}
        subtitle={template.description}
        backLink={{ href: "/", label: "Choose a different document" }}
      />

      <div className="grid flex-1 grid-cols-1 gap-8 lg:grid-cols-2 lg:items-stretch">
        <div className="flex h-[32rem] flex-col gap-4 rounded-xl border border-border bg-card p-6 shadow-sm sm:p-7 lg:h-[calc(100vh-15rem)]">
          <div ref={threadRef} className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  {message.content}
                </div>
              </div>
            ))}
            {isSending && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-lg bg-muted px-3.5 py-2.5 text-sm text-muted-foreground">
                  <ArrowsClockwise size={14} weight="bold" className="animate-spin" />
                  Thinking…
                </div>
              </div>
            )}
          </div>

          {suggestedTemplate && (
            <Link
              href={`/documents/${suggestedTemplate.id}`}
              className="inline-flex w-fit items-center gap-2 rounded-lg border border-border bg-muted px-3.5 py-2 text-sm font-medium text-foreground shadow-sm transition-colors duration-200 hover:bg-border"
            >
              Start a {suggestedTemplate.title} instead
            </Link>
          )}

          {error && <p className="text-xs text-destructive">{error}</p>}
          {saveFailed && (
            <p className="text-xs text-muted-foreground">Couldn&apos;t save your progress. Your chat will keep going, but this turn wasn&apos;t saved.</p>
          )}

          <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-border pt-4">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message…"
              disabled={isSending}
              autoFocus
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card"
            />
            <button
              type="submit"
              disabled={isSending || !input.trim()}
              aria-label="Send message"
              className="inline-flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-md bg-primary text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
            >
              <PaperPlaneTilt size={18} weight="fill" />
            </button>
          </form>

          <div className="flex flex-col gap-2">
            {missingRequiredFields.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {missingRequiredFields.length} more required field
                {missingRequiredFields.length === 1 ? "" : "s"} to fill in before you can
                download.
              </p>
            )}
            <button
              type="button"
              onClick={handleDownload}
              disabled={missingRequiredFields.length > 0 || isGeneratingPdf}
              className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
            >
              {isGeneratingPdf ? (
                <>
                  <ArrowsClockwise size={18} weight="bold" className="animate-spin" />
                  Generating PDF…
                </>
              ) : (
                <>
                  <DownloadSimple size={18} weight="bold" />
                  Download as PDF
                </>
              )}
            </button>
          </div>
        </div>

        <div className="flex h-[32rem] flex-col gap-3 lg:sticky lg:top-10 lg:h-[calc(100vh-15rem)]">
          <div className="flex shrink-0 items-center gap-2 text-sm font-medium text-muted-foreground">
            <FileText size={18} />
            Live preview
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-border bg-paper p-8 font-serif text-base leading-7 whitespace-pre-wrap text-paper-foreground shadow-md sm:p-10">
            {filledBody}
          </div>
          {template.disclaimer && (
            <p className="shrink-0 text-xs leading-relaxed text-muted-foreground">{template.disclaimer}</p>
          )}
        </div>
      </div>
    </div>
  );
}
