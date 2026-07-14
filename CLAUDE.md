# Prelegal Project

## Overview

This is a SaaS product to allow users to draft legal agreements based on templates in the templates directory.
The user can carry out AI chat in order to establish what document they want and how to fill in the fields.
The available documents are covered in the catalog.json file in the project root, included here:

@catalog.json

The current implementation is a technical foundation only: a Mutual NDA creator form (no AI chat yet) served as a static frontend by a FastAPI backend, with a `users` table schema in SQLite but no auth endpoints wired up yet.

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
The database should use SQLLite and be created from scratch each time the Docker container is brought up, allowing for a users table with sign up and sign in.  
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

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)
- Dark Navy: `#032147` (headings)
- Gray Text: `#888888`

## Implementation Status

### Completed (PL-2)

- Dataset of legal document templates in `data/templates/` (8 template types + schema + manifest)

### Completed (PL-3)

- Mutual NDA creator prototype: client-side form with live preview and PDF download (frontend only, no backend)

### Completed (PL-4)

- Docker multi-stage build (Node frontend build stage + Python/uv backend runtime stage)
- FastAPI backend in `backend/` with SQLite recreated from scratch on every container start
- `users` table schema only (id, email, password_hash, created_at) - no auth endpoints yet, that's future work
- Next.js static export (`output: "export"`) served by FastAPI at localhost:8000
- Start/stop scripts for Mac, Linux, Windows (`scripts/`)
- Mutual NDA form unchanged from PL-3 (client-side, no backend wiring yet)

### Not yet started (PL-5, PL-6, PL-7)

- AI chat interface for document creation
- Support for document types beyond the Mutual NDA
- Functional user authentication (signup/signin/signout endpoints, JWT sessions)
- Document persistence and a "My Documents" view

### Current API Endpoints

- `GET /api/health` - Health check
