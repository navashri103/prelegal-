#!/usr/bin/env bash
set -euo pipefail

docker rm -f prelegal >/dev/null 2>&1 || true

echo "Prelegal stopped"
