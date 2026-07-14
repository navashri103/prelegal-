# Prelegal Project

## Overview

This is a SaaS product to allow users to draft legal agreements based on templates in the templates directory.
The user can carry out AI chat in order to establish what document they want and how to fill in the fields.
The available documents are covered in the catalog.json file in the project root, included here:

@catalog.json

The current implementation is a technical foundation only - see Implementation Status below for what's actually built vs. still planned.

## Development process

When instructed to build a feature:

1. Use your Atlassian tools to read the feature instructions from Jira
2. Develop the feature - do not skip any step from the feature-dev 7 step process
3. Thoroughly test the feature with unit tests and integration tests and fix any issues
4. Submit a PR using your github tools

## AI design

I want u to use free ai model that help us with the llm i dont want paid vrsn of openrouter and fast response too

## Technical design

The entire project should be packaged into a Docker container.  
The backend should be in backend/ and be a uv project, using FastAPI.  
The frontend should be in frontend/  
The database uses SQLite. As of PL-7 it persists across restarts via a Docker named volume
(`prelegal-db:/app/db`) so accounts and saved documents survive - it's only ever created fresh
against a brand-new, empty volume, not wiped on every container start.  
Consider statically building the frontend and serving it via FastAPI, if that will work.  
There should be scripts in scripts/ for:

```bash
# Mac
scripts/start-mac.sh    # Start
scripts/stop-mac.sh     # Stop

# Linux
scripts/start-linux.sh
scripts/stop-linux.sh

# Windows
scripts/start-windows.ps1
scripts/stop-windows.ps1
```

Backend available at http://localhost:8000

## Color Scheme

Defined as CSS custom properties in `frontend/app/globals.css` (light mode in `:root`, dark mode
in `.dark`) - this replaces an earlier yellow/purple palette that was documented here but never
actually implemented:

| Token | Light | Dark | Used for |
| --- | --- | --- | --- |
| `--background` | `#eceae4` | `#0b1220` | page background |
| `--foreground` | `#0f172a` | `#e2e8f0` | body text |
| `--card` | `#ffffff` | `#131b2e` | panels (chat, forms) |
| `--muted` | `#f1efe9` | `#1e293b` | subtle backgrounds |
| `--muted-foreground` | `#5b5f6a` | `#94a3b8` | secondary text |
| `--border` | `#dad6cc` | `#263449` | borders |
| `--paper` | `#fffdf8` | `#17202e` | document preview background |
| `--primary` | `#2563eb` | `#3b82f6` | buttons, links (submit actions) |
| `--primary-hover` | `#1d4ed8` | `#60a5fa` | button/link hover |
| `--destructive` | `#dc2626` | `#f87171` | error text |

## Implementation Status

### Completed (PL-2)

- Dataset of 8 legal document templates in `data/templates/` (manifest + JSON schema), only `nda.json` is wired up to the frontend so far

### Completed (PL-3)

- Mutual NDA creator: client-side React form with live preview and PDF download (jspdf) - no backend involved

### Completed (PL-4)

- Docker multi-stage build (Node build stage for the frontend + Python/uv runtime stage for the backend)
- FastAPI backend in `backend/` with SQLite recreated from scratch on every container start
- `users` table schema only (id, email, password_hash, created_at) - no signup/signin endpoints yet
- Next.js static export (`output: "export"`) served by FastAPI at localhost:8000
- Start/stop scripts for Mac, Linux, Windows in `scripts/`
- NDA form unchanged from PL-3 (still fully client-side)

### Completed (PL-5)

- AI chat interface replaces the manual NDA form - freeform conversation, still Mutual NDA only
- Backend calls OpenRouter's free `google/gemma-4-26b-a4b-it:free` model (confirmed $0 cost) with a strict
  JSON schema (`response_format`) to extract field values from the conversation; one automatic retry on
  malformed/empty model responses before surfacing a friendly error
- Fully stateless: frontend holds chat history + field values in React state and sends both on every
  request; backend has no session or persistence (reloading the page loses progress - that's by design,
  document persistence is separate future scope)
- Live preview and PDF download unchanged from PL-3/PL-4, now driven by AI-extracted fields instead of
  manual typing
- Requires an `OPENROUTER_API_KEY` in a gitignored `.env` file at the project root (see `.env.example`);
  start scripts pass it to the container via `--env-file .env` and fail fast with a clear message if
  `.env` is missing

### Completed (PL-6)

- All 8 document types from `data/templates/` are now wired up, not just NDA
- New landing page at `/` lists every document as a card, grouped by category (from `data/templates/index.json`);
  clicking one navigates to that document's own chat page at `/documents/{id}` (static-exported via
  `generateStaticParams`, so all 8 pages are pre-rendered at build time)
- Backend template loading moved to `backend/app/document_templates.py` (manifest lookup + per-id template
  loading, `TemplateNotFoundError` → 404), separate from `backend/app/chat.py`'s LLM orchestration; both chat
  endpoints now take `template_id` as a URL path segment: `GET /api/chat/{template_id}/greeting` and
  `POST /api/chat/{template_id}/message`
- `backend/data/templates/` (a manually-duplicated single-file copy) was deleted; the backend now reads
  templates from the same root `data/templates/` the frontend already used, copied into the Docker image via
  `COPY data/ /data/` in the backend stage
- The AI is now guaranteed (not just prompt-instructed) to ask a follow-up question whenever a required field
  is still missing: `chat.py`'s `_ensure_follow_up()` appends a canned question naming the next 1-2 missing
  required fields if the model's reply doesn't already read as a question - applies to both the opening
  greeting and every mid-conversation turn
- Fixed a UI bug where the chat input didn't reliably regain keyboard focus after the AI replied
  (`inputRef.current?.focus()` was called synchronously right after `setIsSending(false)`, which could race
  ahead of React's DOM update and silently no-op on a still-disabled input); moved to a `useEffect` keyed on
  `isSending` so it always fires after the input is actually re-enabled
- Fixed a latent bug where the downloaded PDF was always named `mutual-nda.pdf` regardless of document type;
  now named `{template_id}.pdf`
- `next.config.ts` gained `trailingSlash: true` - required because the backend serves the static export via
  Starlette's `StaticFiles(html=True)`, which only resolves `<path>/index.html` for a directory request, not
  Next's default flat `<path>.html` files
- Renamed `frontend/lib/nda-template.ts` → `document-template.ts` and `NdaCreator` → `DocumentCreator`
  (moved to `frontend/app/documents/[id]/document-creator.tsx`), since neither was NDA-specific anymore

### Completed (PL-7)

- Full signup/signin/signout: passwords hashed with `bcrypt`, sessions stored server-side in a new
  `sessions` table keyed by a SHA-256 hash of a random token (never the raw token), delivered to the
  browser as an `HttpOnly`, `SameSite=Lax` cookie. New backend module `backend/app/auth.py`.
- Guest access is unchanged from PL-5/PL-6 - anyone can still create and download any document
  without an account. Logging in additionally unlocks document persistence: a new `documents` table
  (one row per in-progress/completed document, `fields`/`messages` stored as JSON) in
  `backend/app/documents.py`. A document is created automatically when a logged-in user opens a
  document page, and saved automatically (via `PUT /api/documents/{id}`) after every chat turn - no
  explicit "Save" button.
- New `/my-documents` page lists a logged-in user's saved documents (status, last-updated, resume/delete);
  resuming a document loads it via `/documents/{template_id}?doc={id}`, which hydrates the saved
  chat history and fields instead of starting a fresh greeting.
- New `/login` and `/signup` pages.
- DB persistence policy changed: `init_db()` no longer wipes the SQLite file on startup (idempotent
  `CREATE TABLE IF NOT EXISTS`); the file lives in a Docker named volume (`prelegal-db:/app/db`, see
  `Dockerfile`/`scripts/start-*`) so it survives container restarts - this intentionally supersedes
  the original "recreated from scratch each time" rule in Technical design above.
- PL-6 gap fix: if a user's chat message asks for a document type outside the current one, the AI no
  longer tries to extract fields for the wrong template - `_response_schema()` gained an
  enum-constrained, server-revalidated `requested_different_document` field, and the frontend renders
  a clickable "Start a {title} instead" link when it's set.
- Final polish: extracted the page header (previously duplicated in `page.tsx` and
  `document-creator.tsx`) into a shared, auth-aware `frontend/app/page-header.tsx`; fixed the
  Color Scheme section above to match the CSS tokens actually in use.

### Current API Endpoints

- `GET /api/health` - Health check
- `GET /api/chat/{template_id}/greeting` - Get the AI's opening message and empty field state for a given
  document type (404 if `template_id` is unknown)
- `POST /api/chat/{template_id}/message` - Send the full chat history + known fields for a given document
  type, get back the AI's reply, updated fields, and (PL-7) a `suggested_template_id` if the user asked
  for a different document type (404 if `template_id` is unknown)
- `POST /api/auth/signup` / `POST /api/auth/login` - Create or authenticate a user, sets the session cookie
- `POST /api/auth/logout` - Clear the current session (no-op if already signed out)
- `GET /api/auth/me` - Current signed-in user, 401 if signed out
- `POST /api/documents` - Create a new saved document for the current template (401 if signed out)
- `GET /api/documents` - List the current user's saved documents (401 if signed out)
- `GET /api/documents/{id}` / `PUT /api/documents/{id}` / `DELETE /api/documents/{id}` - Fetch, save
  progress on, or delete one of the current user's documents (401 if signed out, 404 if the id
  doesn't belong to them)

### Known gaps

- This file references `@catalog.json` at the project root, but no such file exists - the closest thing is `data/templates/index.json` (from PL-2), which isn't a root-level catalog
- Auth (PL-7) deliberately has no password reset, email verification, or rate limiting on
  signup/login - out of scope for this ticket at "a handful of users" scale
- The session cookie's `Secure` flag defaults off (`PRELEGAL_COOKIE_SECURE=false`) since the app is
  served over plain HTTP in local Docker use; set that env var to `true` if ever deployed behind HTTPS
