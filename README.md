# Research Pipeline Studio

Research Pipeline Studio is a local-first, stepwise research-to-paper system with auditability, approval gating, citation verification, and experiment execution support for local, SSH, and Slurm environments.

## Features

- Project management with step-by-step workflow (Part 1 → Final)
- Approval/lock state to prevent overwriting outputs
- Run history, diffs, and rollback-ready run storage
- Execution plans with explicit approval before local/remote run
- Citation verification via Crossref; unverified citations are marked and excluded from default bibliography
- Results guardrails: Final step warns if `metrics.json` is missing
- Export LaTeX projects and compile PDFs via `latexmk` when installed

## Requirements

- Python 3.11+
- Node.js 18+

## Quick Start

```bash
make doctor
make dev
```

The backend runs at `http://localhost:8000` and the frontend at `http://localhost:5173`.

Health check: `GET http://localhost:8000/api/health`

## Environment Variables

```bash
export GEMINI_API_KEY=your_key
export GEMINI_MODEL=gemini-1.5-pro
export OPENAI_API_KEY=your_key   # optional
export OPENAI_MODEL=gpt-4o-mini   # optional
export ANTHROPIC_API_KEY=your_key # optional
export ANTHROPIC_MODEL=claude-3-5-sonnet-20240620 # optional
```

## Makefile Targets

- `make dev` - start backend + frontend
- `make test` - run backend tests
- `make demo` - load example project

## Tests

Run the full test suite:

```bash
make test
```

Coverage includes schema validation, workflow transitions (run/edit/approve/unlock), citation verification with stubbed responses, execution approval gating, and results gating for Final without metrics.json.

## Project Structure

```
/backend   FastAPI backend
/frontend  React + Vite frontend
/prompts   Versioned prompt templates
/examples  Demo project artifacts
/docs      Setup and design notes
```

## Notes

- The execution layer enforces an explicit plan + approval before any command runs.
- PDF export requires `latexmk` installed. If unavailable, the system provides `.tex` exports.

## LaTeX/PDF Export Setup

Install `latexmk`:

- macOS (Homebrew): `brew install latexmk`
- Ubuntu/Debian: `sudo apt-get install latexmk texlive-full`

PDF export attempts `latexmk` automatically. If it is missing, the UI shows a warning and the LaTeX zip download remains available.

## How to verify Task 3 (Guardrails)

1. Start the app: `make dev`.
2. Create a project and run Part 1–3.
3. Go to Final without Part 4 ingestion:
   - The Run button is blocked and a warning appears to ingest metrics first.
4. In Part 1, include a citation that will remain unverified:
   - The Citation Status card shows it as UNVERIFIED.
   - `artifacts/latex/references.bib` excludes it by default.

## How to verify Task 5 (UI workflow + artifacts)

1. Start the app: `make dev`.
2. Create a project and select Part 1.
3. Click **Run**, then **Approve** to lock it; confirm the Run button disables and “Locked” status appears.
4. Click **Unlock**, then **Re-run** to create a new run.
5. Use the **Run History** list:
   - Click **Load** to view an older run in the output editor.
   - Click **Rollback** to set an older run as the active output (via a manual edit run).
6. In the Artifact viewer, switch tabs (Markdown/JSON/Citation Status/LaTeX/PDF) and select artifacts from the dropdown.
   - If a PDF artifact exists, it should render in the PDF tab.
