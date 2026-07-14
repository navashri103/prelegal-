"use client";

import { useMemo, useState } from "react";
import { fillTemplateBody, type Template, type TemplateField } from "@/lib/nda-template";

type FieldValues = Record<string, string>;

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: TemplateField;
  value: string;
  onChange: (key: string, value: string) => void;
}) {
  const commonProps = {
    id: field.key,
    name: field.key,
    value,
    placeholder: field.placeholder,
    required: field.required,
    onChange: (
      e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => onChange(field.key, e.target.value),
    className:
      "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100",
  };

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={field.key} className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
        {field.label}
        {field.required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      {field.type === "textarea" ? (
        <textarea {...commonProps} rows={3} />
      ) : (
        <input
          {...commonProps}
          type={field.type === "number" ? "number" : field.type === "date" ? "date" : field.type === "email" ? "email" : "text"}
        />
      )}
    </div>
  );
}

export default function NdaCreator({ template }: { template: Template }) {
  const [values, setValues] = useState<FieldValues>(() =>
    Object.fromEntries(template.fields.map((field) => [field.key, ""]))
  );
  const [isGenerating, setIsGenerating] = useState(false);

  const handleChange = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  const missingRequiredFields = useMemo(
    () => template.fields.filter((field) => field.required && !values[field.key]?.trim()),
    [values, template.fields]
  );

  const filledBody = useMemo(
    () => fillTemplateBody(template.body, values, template.fields),
    [values, template.body, template.fields]
  );

  const handleDownload = async () => {
    setIsGenerating(true);
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
      setIsGenerating(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-10 sm:px-10">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          {template.title} Creator
        </h1>
        <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          {template.description}
        </p>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-8 lg:grid-cols-2">
        <form
          className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-zinc-50 p-6 dark:border-zinc-800 dark:bg-zinc-900/40"
          onSubmit={(e) => e.preventDefault()}
        >
          {template.fields.map((field) => (
            <FieldInput key={field.key} field={field} value={values[field.key]} onChange={handleChange} />
          ))}

          <div className="mt-2 flex flex-col gap-2">
            {missingRequiredFields.length > 0 && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Fill in all required fields to enable download (
                {missingRequiredFields.length} remaining).
              </p>
            )}
            <button
              type="button"
              onClick={handleDownload}
              disabled={missingRequiredFields.length > 0 || isGenerating}
              className="inline-flex items-center justify-center rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300 dark:disabled:bg-zinc-700"
            >
              {isGenerating ? "Generating PDF…" : "Download as PDF"}
            </button>
          </div>
        </form>

        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Live preview</h2>
          <div className="flex-1 overflow-auto rounded-lg border border-zinc-200 bg-white p-6 font-serif text-sm leading-6 whitespace-pre-wrap text-zinc-900 shadow-sm dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100">
            {filledBody}
          </div>
          {template.disclaimer && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400">{template.disclaimer}</p>
          )}
        </div>
      </div>
    </div>
  );
}
