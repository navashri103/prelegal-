import { loadTemplateManifest } from "@/lib/template-loader";
import DocumentList from "./document-list";

export default function MyDocumentsPage() {
  const templates = loadTemplateManifest();
  return <DocumentList templates={templates} />;
}
