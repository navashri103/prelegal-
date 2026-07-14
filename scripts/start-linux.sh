#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Missing .env file. Copy .env.example to .env and add your OPENROUTER_API_KEY." >&2
  exit 1
fi

docker build -t prelegal .
docker rm -f prelegal >/dev/null 2>&1 || true
docker run -d --name prelegal -p 8000:8000 --env-file .env prelegal

echo "Prelegal is starting at http://localhost:8000"
