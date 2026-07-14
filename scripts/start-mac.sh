#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker build -t prelegal .
docker rm -f prelegal >/dev/null 2>&1 || true
docker run -d --name prelegal -p 8000:8000 prelegal

echo "Prelegal is starting at http://localhost:8000"
