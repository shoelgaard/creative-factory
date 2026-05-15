#!/usr/bin/env bash
# Creative Factory — one-shot setup.
# Idempotent: rerun safely.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "[cf-setup] root: $ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[cf-setup] python3 not found in PATH" >&2
  exit 1
fi

PYV="$(python3 --version)"
echo "[cf-setup] $PYV"

# Optional certifi for clean SSL — install only if missing
if ! python3 -c "import certifi" 2>/dev/null; then
  echo "[cf-setup] installing certifi (user-site)"
  python3 -m pip install --user --quiet certifi || \
    echo "[cf-setup] WARN: certifi install failed, will fall back to system trust store"
fi

# .env scaffold
if [ ! -f .env ]; then
  echo "[cf-setup] creating .env from .env.example"
  cp .env.example .env
  echo "[cf-setup] EDIT .env and add your GEMINI_API_KEY (and optionally FAL_API_KEY)"
fi

mkdir -p references output

# Make CLI + engine clients executable
chmod +x interfaces/cli/cf.py engines/gemini-veo/client.py engines/fal/client.py 2>/dev/null || true

echo "[cf-setup] done. Run:  python3 interfaces/cli/cf.py editorial gen --image references/<file> --brand persillo"
