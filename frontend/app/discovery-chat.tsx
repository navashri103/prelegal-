"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowsClockwise, PaperPlaneTilt } from "@phosphor-icons/react/ssr";
import { apiGet, apiPost } from "@/lib/api";

type ChatMessage = { role: "user" | "assistant"; content: string };
type DiscoverResponse = { reply: string; matched_template_id: string | null };

const REDIRECT_DELAY_MS = 900;

export default function DiscoveryChat() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<DiscoverResponse>("/api/discover/greeting")
      .then((data) => {
        if (!cancelled) setMessages([{ role: "assistant", content: data.reply }]);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't reach the assistant. Please refresh to try again.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isSending) inputRef.current?.focus();
  }, [isSending]);

  // Cancel a pending redirect if this component unmounts first (e.g. the user
  // clicks a document card to navigate away manually before the delay fires) -
  // otherwise the stale timer would still push a route change afterward.
  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
    };
  }, []);

  const sendMessage = async (content: string) => {
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setIsSending(true);
    setError(null);
    try {
      const data = await apiPost<DiscoverResponse>("/api/discover/message", { messages: nextMessages });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      if (data.matched_template_id) {
        const templateId = data.matched_template_id;
        redirectTimerRef.current = setTimeout(
          () => router.push(`/documents/${templateId}/`),
          REDIRECT_DELAY_MS
        );
      }
    } catch {
      setError("Something went wrong. Please try again.");
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

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-2">
        {messages.map((message, index) => (
          <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
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

      {error && <p className="text-xs text-destructive">{error}</p>}

      <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-border pt-3">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. I need to lease out my apartment…"
          disabled={isSending}
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
    </div>
  );
}
