import Link from "next/link";
import { ShieldCheck } from "@phosphor-icons/react/ssr";
import { loadAllTemplates } from "@/lib/template-loader";
import ThemeToggle from "./theme-toggle";

export default function Home() {
  const templates = loadAllTemplates();
  const categories = Array.from(new Set(templates.map((t) => t.category))).sort();

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-6 py-10 sm:px-10">
      <header className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <ShieldCheck size={22} weight="fill" />
          </span>
          <div className="flex flex-col gap-1">
            <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
              Prelegal
            </h1>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Chat with an AI assistant to draft a legal document, then download it as a PDF.
            </p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <div className="flex flex-col gap-8">
        {categories.map((category) => (
          <section key={category} className="flex flex-col gap-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {category}
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {templates
                .filter((template) => template.category === category)
                .map((template) => (
                  <Link
                    key={template.id}
                    href={`/documents/${template.id}`}
                    className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-5 shadow-sm transition-colors duration-200 hover:bg-muted"
                  >
                    <span className="font-serif text-lg font-semibold text-foreground">
                      {template.title}
                    </span>
                    <span className="text-sm leading-relaxed text-muted-foreground">
                      {template.description}
                    </span>
                  </Link>
                ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
