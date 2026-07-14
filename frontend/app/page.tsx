import Link from "next/link";
import { loadAllTemplates } from "@/lib/template-loader";
import PageHeader from "./page-header";

export default function Home() {
  const templates = loadAllTemplates();
  const categories = Array.from(new Set(templates.map((t) => t.category))).sort();

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-6 py-10 sm:px-10">
      <PageHeader
        title="Prelegal"
        subtitle="Chat with an AI assistant to draft a legal document, then download it as a PDF."
      />

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
