# Research Progress Tracker

A clean, project-based research diary that tracks your work across stages:

**Idea → Related Work → Method → Experiments → Results → Draft → Submission**

Each stage supports:
- Marking completion
- Uploading files (PDFs, CSVs, docs, etc.)
- Reviewing uploaded evidence

## Requirements

- Python 3.11+
- Node.js 18+

## Quick Start

```bash
make dev
```

Backend: http://localhost:8000  
Frontend: http://localhost:5173

## How it works

1. Create a project.
2. Click a stage to open it.
3. Mark completion and upload relevant files.
4. Move through stages as you progress.

## Windows setup

If you don’t have `make`, run manually:

### Terminal 1 (Backend)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2 (Frontend)
```powershell
cd frontend
npm install
npm run dev
```

## Health check

```bash
GET http://localhost:8000/api/health
```
