"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowsClockwise,
  DownloadSimple,
  FileText,
  PaperPlaneTilt,
  ShieldCheck,
} from "@phosphor-icons/react/ssr";
import { fillTemplateBody, type Template } from "@/lib/nda-template";
import ThemeToggle from "./theme-toggle";

type FieldValues = Record<string, string>;
type ChatRole = "user" | "assistant";
type ChatMessage = { role: ChatRole; content: string };
type ChatApiResponse = { reply: string; fields: Record<string, string | null> };

function emptyFieldValues(template: Template): FieldValues {
  return Object.fromEntries(template.fields.map((field) => [field.key, ""]));
}

function nullableToFieldValues(fields: Record<string, string | null>): FieldValues {
  return Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, value ?? ""]));
}

export default function NdaCreator({ template }: { template: Template }) {
  const [values, setValues] = useState<FieldValues>(() => emptyFieldValues(template));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch("/api/chat/greeting");
        if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
        const data: ChatApiResponse = await response.json();
        if (cancelled) return;
        setMessages([{ role: "assistant", content: data.reply }]);
        setValues(nullableToFieldValues(data.fields));
      } catch {
        if (cancelled) return;
        setError("Couldn't reach the assistant. Please refresh the page to try again.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const missingRequiredFields = useMemo(
    () => template.fields.filter((field) => field.required && !values[field.key]?.trim()),
    [values, template.fields]
  );

  const filledBody = useMemo(
    () => fillTemplateBody(template.body, values, template.fields),
    [values, template.body, template.fields]
  );

  const sendMessage = async (content: string) => {
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setIsSending(true);
    setError(null);
    try {
      const response = await fetch("/api/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages, fields: values }),
      });
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const data: ChatApiResponse = await response.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      setValues(nullableToFieldValues(data.fields));
    } catch {
      setError("Something went wrong sending that message. Please try again.");
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
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

      doc.save("mutual-nda.pdf");
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-10 sm:px-10">
      <header className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <ShieldCheck size={22} weight="fill" />
          </span>
          <div className="flex flex-col gap-1">
            <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
              {template.title}
            </h1>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {template.description}
            </p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <div className="grid flex-1 grid-cols-1 gap-8 lg:grid-cols-2 lg:items-start">
        <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6 shadow-sm sm:p-7">
          <div className="flex max-h-[28rem] min-h-[20rem] flex-col gap-3 overflow-y-auto pr-1">
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
            <div ref={threadEndRef} />
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}

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

        <div className="flex flex-col gap-3 lg:sticky lg:top-10">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <FileText size={18} />
            Live preview
          </div>
          <div className="rounded-xl border border-border bg-paper p-8 font-serif text-base leading-7 whitespace-pre-wrap text-paper-foreground shadow-md sm:p-10">
            {filledBody}
          </div>
          {template.disclaimer && (
            <p className="text-xs leading-relaxed text-muted-foreground">{template.disclaimer}</p>
          )}
        </div>
      </div>
    </div>
  );
}
