import { Suspense } from "react";
import { notFound } from "next/navigation";
import { loadTemplate, loadTemplateManifest } from "@/lib/template-loader";
import DocumentCreator from "./document-creator";

export function generateStaticParams() {
  return loadTemplateManifest().map((entry) => ({ id: entry.id }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const template = loadTemplate(id);
    return { title: template.title, description: template.description };
  } catch {
    return {};
  }
}

export default async function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const template = loadTemplate(id);
    const templates = loadTemplateManifest();
    return (
      <Suspense>
        <DocumentCreator template={template} templates={templates} />
      </Suspense>
    );
  } catch {
    notFound();
  }
}
