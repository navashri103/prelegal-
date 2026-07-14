export type TemplateFieldType = "text" | "textarea" | "date" | "number" | "email";

export interface TemplateField {
  key: string;
  label: string;
  type: TemplateFieldType;
  required: boolean;
  placeholder?: string;
}

export interface Template {
  id: string;
  title: string;
  category: string;
  description: string;
  disclaimer?: string;
  fields: TemplateField[];
  body: string;
}

export interface TemplateManifestEntry {
  id: string;
  title: string;
  category: string;
  file: string;
}

export function fillTemplateBody(
  body: string,
  values: Record<string, string>,
  fields: TemplateField[]
): string {
  return fields.reduce((text, field) => {
    const value = values[field.key]?.trim();
    const token = `{{${field.key}}}`;
    return text.split(token).join(value || `[${field.label}]`);
  }, body);
}
