# Remediation Plan — Research Pipeline Studio

## 1) Implement ingestion pipeline (blocking for results gating)
- Add ingestion service in `backend/app/ingestion.py` that:
  - Accepts uploads or execution outputs.
  - Normalizes metrics to `metrics.json`.
  - Generates `tables/*.tex`, `figures/*.png`, and `results_summary.md`.
- Update Part 4 workflow (`backend/app/workflow.py`) to call ingestion pipeline.
- Expose ingestion status in `GET /api/projects/{id}/artifacts` and in UI.

## 2) Enforce results gating and verified citations
- Enforce Final step blocking when `metrics.json` missing (return error or suppress Results section content).
- Populate `references.bib` from verified citations only (exclude unverified by default).
- Add UI warnings for missing evidence and unverified citations.

## 3) Complete execution layer for SSH/Slurm
- Implement SFTP staging and artifact collection in `SSHRunner`.
- Implement Slurm lifecycle:
  - Generate sbatch script
  - `sbatch` submit; capture job id
  - Poll `squeue`
  - Fetch `slurm-*.out` or configured output files
  - Implement `scancel`
- Implement cancel for Local/SSH/Slurm runners and wire `/cancel` endpoint.

## 4) Expand UI workflow controls
- Add inline editor that calls `/steps/{step_id}/edit`.
- Add run rollback: new endpoint to set current run or mark run as approved, with UI selection.
- Show step lock state and approval status in UI.
- Add artifact viewer tabs (Markdown/JSON/LaTeX/PDF preview).

## 5) Provider defaults and settings
- Add project settings UI panel (venue template, provider defaults, cluster profiles).
- Wire backend settings to apply default provider/model per step.
- Use env var defaults for GEMINI/OPENAI/ANTHROPIC models when UI not specified.

## 6) LaTeX/PDF enhancements
- Generate section content from approved artifacts and step outputs.
- Add PDF preview or download in UI.

## 7) Add missing API endpoints
- Implement `/api/projects/{id}/executions/{exec_id}/cancel` and `/collect`.
- Add a rollback endpoint: `/api/projects/{id}/steps/{step_id}/rollback`.
