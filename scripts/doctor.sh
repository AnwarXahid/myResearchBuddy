#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

printf "== Research Pipeline Studio Doctor ==\n"

printf "\n[Node/NPM]\n"
if command -v node >/dev/null 2>&1; then
  node -v
else
  echo "node: NOT FOUND (install Node.js 18+)"
fi
if command -v npm >/dev/null 2>&1; then
  npm -v
else
  echo "npm: NOT FOUND"
fi

printf "\n[NPM Registry]\n"
if command -v npm >/dev/null 2>&1; then
  npm config get registry
  echo "If you see 403 errors, try:"
  echo "  npm config set registry https://registry.npmjs.org/"
  echo "Or configure your org mirror/registry per policy."
fi

printf "\n[Python]\n"
if command -v python >/dev/null 2>&1; then
  python --version
else
  echo "python: NOT FOUND (install Python 3.11+)"
fi

printf "\n[Backend Virtualenv]\n"
if [ -d "$BACKEND_DIR/.venv" ]; then
  echo "backend/.venv: present"
else
  echo "backend/.venv: missing"
  echo "Create with: python -m venv backend/.venv"
  echo "Then: source backend/.venv/bin/activate"
fi

printf "\n[Backend Dependencies]\n"
if command -v python >/dev/null 2>&1; then
  if python -m pip show uvicorn >/dev/null 2>&1; then
    echo "uvicorn: installed"
  else
    echo "uvicorn: missing"
    echo "Install with: (cd backend && pip install -e .)"
  fi
fi

printf "\n[Frontend Dependencies]\n"
if [ -d "$FRONTEND_DIR/node_modules" ]; then
  echo "frontend/node_modules: present"
else
  echo "frontend/node_modules: missing"
  echo "Install with: (cd frontend && npm install)"
fi
