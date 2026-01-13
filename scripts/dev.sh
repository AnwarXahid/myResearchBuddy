#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if ! command -v python >/dev/null 2>&1; then
  echo "python is required (3.11+)."
  exit 1
fi

if ! python -m pip show uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found. Install backend deps with:"
  echo "  (cd backend && pip install -e .)"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required (Node.js 18+)."
  exit 1
fi

if ! (cd "$FRONTEND_DIR" && npm install); then
  echo "npm install failed. If you saw a 403, set registry with:"
  echo "  npm config set registry https://registry.npmjs.org/"
  echo "Or configure your org mirror/registry per policy."
  exit 1
fi

( cd "$BACKEND_DIR" && python -m uvicorn app.main:app --reload --port 8000 ) &
BACKEND_PID=$!

( cd "$FRONTEND_DIR" && npm run dev ) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID' EXIT
wait
