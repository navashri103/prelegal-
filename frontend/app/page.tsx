import fs from "node:fs";
import path from "node:path";
import NdaCreator from "./nda-creator";
import type { Template } from "@/lib/nda-template";

function loadNdaTemplate(): Template {
  const templatePath = path.join(process.cwd(), "..", "data", "templates", "nda.json");
  const raw = fs.readFileSync(templatePath, "utf-8");
  return JSON.parse(raw) as Template;
}

export default function Home() {
  const template = loadNdaTemplate();
  return <NdaCreator template={template} />;
}
