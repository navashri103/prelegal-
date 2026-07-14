// Server-only: reads template JSON off disk at build time. Only import from
// Server Components (e.g. app/page.tsx, app/documents/[id]/page.tsx).
import fs from "node:fs";
import path from "node:path";
import type { Template, TemplateManifestEntry } from "./document-template";

const TEMPLATES_DIR = path.join(process.cwd(), "..", "data", "templates");

export function loadTemplateManifest(): TemplateManifestEntry[] {
  const raw = fs.readFileSync(path.join(TEMPLATES_DIR, "index.json"), "utf-8");
  return (JSON.parse(raw).templates as TemplateManifestEntry[]);
}

export function loadTemplate(templateId: string): Template {
  const entry = loadTemplateManifest().find((t) => t.id === templateId);
  if (!entry) {
    throw new Error(`Unknown document type: ${templateId}`);
  }
  const raw = fs.readFileSync(path.join(TEMPLATES_DIR, entry.file), "utf-8");
  return JSON.parse(raw) as Template;
}

export function loadAllTemplates(): Template[] {
  return loadTemplateManifest().map((entry) => loadTemplate(entry.id));
}
