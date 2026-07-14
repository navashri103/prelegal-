"use client";

import { useMemo, useState } from "react";
import {
  ArrowsClockwise,
  DownloadSimple,
  FileText,
  ShieldCheck,
} from "@phosphor-icons/react/ssr";
import { fillTemplateBody, type Template, type TemplateField } from "@/lib/nda-template";
import ThemeToggle from "./theme-toggle";

type FieldValues = Record<string, string>;

const FIELD_GROUPS: { title: string; keys: string[] }[] = [
  { title: "Effective Date", keys: ["effective_date"] },
  {
    title: "Party A",
    keys: ["party_a_name", "party_a_address", "party_a_signatory_name", "party_a_signatory_title"],
  },
  {
    title: "Party B",
    keys: ["party_b_name", "party_b_address", "party_b_signatory_name", "party_b_signatory_title"],
  },
  {
    title: "Agreement Terms",
    keys: ["purpose", "term_years", "governing_state", "governing_county"],
  },
];

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
      "w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card",
  };

  const isFullWidth = field.type === "textarea";

  return (
    <div className={`flex flex-col gap-1.5 ${isFullWidth ? "sm:col-span-2" : ""}`}>
      <label htmlFor={field.key} className="text-sm font-medium text-foreground">
        {field.label}
        {field.required && (
          <span className="ml-0.5 text-destructive" aria-hidden="true">
            *
          </span>
        )}
        {!field.required && (
          <span className="ml-1.5 text-xs font-normal text-muted-foreground">optional</span>
        )}
      </label>
      {field.type === "textarea" ? (
        <textarea {...commonProps} rows={2} />
      ) : (
        <input
          {...commonProps}
          type={
            field.type === "number"
              ? "number"
              : field.type === "date"
                ? "date"
                : field.type === "email"
                  ? "email"
                  : "text"
          }
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

  const fieldsByKey = useMemo(
    () => new Map(template.fields.map((field) => [field.key, field])),
    [template.fields]
  );

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
        <form
          className="flex flex-col gap-6 rounded-xl border border-border bg-card p-6 shadow-sm sm:p-7"
          onSubmit={(e) => e.preventDefault()}
        >
          {FIELD_GROUPS.map((group) => (
            <fieldset key={group.title} className="flex flex-col gap-4">
              <legend className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {group.title}
              </legend>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {group.keys.map((key) => {
                  const field = fieldsByKey.get(key);
                  if (!field) return null;
                  return (
                    <FieldInput
                      key={field.key}
                      field={field}
                      value={values[field.key]}
                      onChange={handleChange}
                    />
                  );
                })}
              </div>
            </fieldset>
          ))}

          <div className="flex flex-col gap-2 border-t border-border pt-5">
            {missingRequiredFields.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Fill in all required fields to enable download ({missingRequiredFields.length}{" "}
                remaining).
              </p>
            )}
            <button
              type="button"
              onClick={handleDownload}
              disabled={missingRequiredFields.length > 0 || isGenerating}
              className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors duration-200 hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
            >
              {isGenerating ? (
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
        </form>

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
