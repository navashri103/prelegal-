# Stage 1: build the static frontend export
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
COPY data/ /data/
RUN npm run build

# Stage 2: Python backend serving the API and the static frontend
FROM python:3.13-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /usr/local/bin/
WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/app ./app
COPY data/ /data/
RUN uv sync --locked --no-dev

COPY --from=frontend-build /frontend/out ./static

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
