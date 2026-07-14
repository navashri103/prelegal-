# Legal Document Templates Dataset

This directory contains the initial dataset of legal document templates
(PL-2). The system will use these as a starting point that it can later
fill in and modify on behalf of a user.

## Structure

- `index.json` — manifest listing every available template (`id`, `title`,
  `category`, and the file that holds its content).
- `schema/template.schema.json` — JSON Schema describing the shape of a
  single template file, for validation.
- `<template_id>.json` — one file per template, containing:
  - `id`, `title`, `category`, `description`, `disclaimer`
  - `fields` — the ordered list of fillable fields (`key`, `label`, `type`,
    `required`, optional `placeholder`)
  - `body` — the full document text with `{{field_key}}` placeholders that
    correspond 1:1 to entries in `fields`

## Usage

A future template-filling system should:
1. Read `index.json` to list templates available to a user.
2. Load the referenced template file and present `fields` as a form.
3. Substitute each `{{field_key}}` token in `body` with the user-provided
   (or system-generated) value to produce the final document, and allow
   further edits before finalizing.

## Included templates

| ID | Title | Category |
| --- | --- | --- |
| `nda` | Non-Disclosure Agreement (NDA) | Business |
| `rental_agreement` | Residential Rental/Lease Agreement | Real Estate |
| `employment_offer_letter` | Employment Offer Letter | Employment |
| `power_of_attorney` | General Power of Attorney | Personal |
| `cease_and_desist_letter` | Cease and Desist Letter | Personal |
| `last_will_and_testament` | Last Will and Testament | Personal |
| `service_agreement` | Service Agreement | Business |
| `affidavit` | General Affidavit | Personal |

## Disclaimer

These templates are generic starting points for informational purposes
only. They are not a substitute for advice from a licensed attorney, and
requirements (e.g. notarization, witnesses, mandatory clauses) vary by
jurisdiction.
