#!/usr/bin/env bash
set -euo pipefail

( cd backend && python -m uvicorn app.main:app --reload --port 8000 ) &
BACKEND_PID=$!

( cd frontend && npm install && npm run dev ) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID' EXIT
wait
