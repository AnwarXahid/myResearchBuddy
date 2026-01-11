# Acceptance Checklist — Research Pipeline Studio

Date: 2026-01-08

## Summary
Overall status: **NO-GO** — implementation does not fully satisfy the spec. Multiple core requirements are partial or missing, including UI step editing/rollback, execution safety for SSH/Slurm, experiment ingestion, and full guardrails.

---

## A. One-command dev start
**Status:** PASS (with caveats)

**Evidence**
- Top-level `Makefile` exposes `make dev` which runs `scripts/dev.sh` to start backend+frontend in one command.【F:Makefile†L1-L10】
- `scripts/dev.sh` starts uvicorn and Vite concurrently.【F:scripts/dev.sh†L1-L11】

**Reproduction Steps**
1. `make dev`
2. Verify backend at `http://localhost:8000` and frontend at `http://localhost:5173`.

**Notes / Caveats**
- `npm install` is run inside the dev script and may fail in restricted environments.
- `uvicorn` is not pinned as an executable in repo; requires Python env.

---

## B. Local-first web UI (not CLI-only)
**Status:** PARTIAL

**Evidence**
- Project list & create: present in `frontend/src/App.tsx` sidebar and `POST /api/projects` in backend.【F:frontend/src/App.tsx†L151-L168】【F:backend/app/main.py†L54-L83】
- Stepper in workspace: present in `App.tsx` stepper UI.【F:frontend/src/App.tsx†L171-L185】
- Per-step controls: **Run** + **Approve** + **Unlock** present.【F:frontend/src/App.tsx†L187-L217】
- Run history + diff viewer: present in UI and backend diff route.【F:frontend/src/App.tsx†L223-L239】【F:backend/app/main.py†L246-L280】
- Artifact viewer: present only as a plain list (no tabs for Markdown/JSON/LaTeX/PDF).【F:frontend/src/App.tsx†L241-L248】

**Missing / Partial**
- **Edit step outputs in UI**: no inline editor + save; backend supports `/edit` but UI does not call it.
- **Re-run and rollback**: no explicit “set current run”/rollback control; backend has run history but no rollback endpoint.
- **Approval/lock state visibility**: not shown in UI.
- **Project workspace layout with left settings / right artifact tabs**: not implemented.

**Reproduction Steps**
1. `make dev`
2. Create project in UI.
3. Select a step and click **Run**.
4. Observe Run History and Diff viewer.

**Minimal Remediation**
- Add UI editor calling `POST /steps/{step_id}/edit`.
- Add rollback endpoint (e.g., `POST /steps/{step_id}/rollback`) and UI control to select a run as current.
- Add locked state indicator by reading step state in the API.
- Add artifact viewer tabs (Markdown, JSON, LaTeX, PDF preview).

---

## C. Gemini-first provider & pluggable providers
**Status:** PARTIAL

**Evidence**
- Gemini client default in backend `LLMClient` layer, with OpenAI and Anthropic adapters present.【F:backend/app/llm.py†L1-L178】
- UI default provider is `gemini` and default model is `gemini-1.5-pro`.【F:frontend/src/App.tsx†L22-L25】
- Provider/model selectable per step in UI drop-down and input.【F:frontend/src/App.tsx†L187-L207】

**Missing / Partial**
- Backend ignores `GEMINI_MODEL` env var; model selection only from UI, not defaulted in config.
- No per-project defaults in settings UI.

**Reproduction Steps**
1. Set `GEMINI_API_KEY`.
2. Run a step with provider `gemini`.
3. Switch provider to `openai` or `anthropic`.

**Minimal Remediation**
- Read `GEMINI_MODEL` / `OPENAI_MODEL` / `ANTHROPIC_MODEL` defaults in backend or UI.
- Add project settings panel with provider defaults.

---

## D. Guardrails
**Status:** PARTIAL

**Evidence**
- Citation verification via Crossref in `CitationVerifier.verify` and applied in Part 1 step output.【F:backend/app/citations.py†L8-L47】【F:backend/app/workflow.py†L121-L129】
- Results gating: Final step adds TODO if `metrics.json` missing; LaTeX results section TODO inserted.【F:backend/app/workflow.py†L130-L168】

**Missing / Partial**
- No Semantic Scholar or arXiv verification options.
- Unverified citations are **not excluded** from final bibliography; bibliography file is stubbed and not populated with verified-only references.
- UI warnings for unverified citations or missing metrics are missing.
- Final step is still callable without metrics; guardrails are informational only.

**Reproduction Steps**
1. Run Part 1 with related work candidates; verify `status` fields in output.
2. Run Final step without `metrics.json` and inspect generated LaTeX section for TODOs.

**Minimal Remediation**
- Add verification sources beyond Crossref and merge results.
- Generate `references.bib` from verified-only citations.
- Enforce blocking logic for Results section when `metrics.json` missing.
- Add UI warnings for missing evidence.

---

## E. PDF/LaTeX export
**Status:** PARTIAL

**Evidence**
- LaTeX project generation in Final step creates `main.tex` + sections and `references.bib`.【F:backend/app/workflow.py†L130-L168】
- PDF export attempts `latexmk` and falls back to `.tex` with warning.【F:backend/app/main.py†L330-L351】

**Missing / Partial**
- LaTeX content is stubbed; no section content from step artifacts.
- UI lacks PDF preview or download links.

**Reproduction Steps**
1. Run Final step and call `GET /api/projects/{id}/export/latex`.
2. Call `GET /api/projects/{id}/export/pdf` with/without `latexmk` installed.

**Minimal Remediation**
- Render section content based on approved step outputs.
- Provide PDF preview tab in UI.

---

## F. Execution layer with approval gating
**Status:** PARTIAL

**Evidence**
- Planning endpoint exists and does not execute commands; approval endpoint required for execution.【F:backend/app/main.py†L366-L433】
- LocalRunner uses subprocess and logs stdout/stderr, audit log stored with checksums.【F:backend/app/execution.py†L26-L84】
- SSHRunner and SlurmRunner classes exist.【F:backend/app/execution.py†L87-L196】
- UI includes plan → approve → run flow for executions.【F:frontend/src/App.tsx†L250-L271】

**Missing / Partial**
- SSHRunner lacks file staging (SFTP) and artifact collection.
- SlurmRunner does not generate `sbatch` submission, poll `squeue`, or fetch outputs; it only wraps commands.
- No cancel implementation for local/SSH/Slurm; `/cancel` endpoint is stubbed.
- Audit log does not capture immutable logs per command beyond stdout/stderr for local/SSH; no artifact checksums for produced files beyond log files.
- Execution plan approve endpoint uses plan ID but is inconsistent with required API list (missing explicit `POST /executions/{exec_id}/cancel` behavior).

**Reproduction Steps**
1. `POST /api/projects/{id}/executions/plan` with `runner=local`.
2. `POST /api/projects/{id}/executions/plan/{plan_id}/approve`.
3. `POST /api/projects/{id}/executions/run`.

**Minimal Remediation**
- Implement SFTP staging + fetch in `SSHRunner`.
- Implement Slurm submission via `sbatch`, polling via `squeue`, output collection, and cancellation in `SlurmRunner`.
- Implement cancellation logic for each runner.
- Extend audit logs with full command/job metadata and artifact checksums for produced files.

---

## G. Experiment ingestion
**Status:** FAIL

**Evidence**
- Upload endpoint exists but only stores files; no normalization or metrics/tables/figures generation.【F:backend/app/main.py†L282-L304】
- No ingestion pipeline or artifact generators in backend.

**Missing**
- No ingestion-first Part 4 flow.
- No `metrics.json` generation from uploads or execution outputs.
- No tables/figures generation, no `results_summary.md`.

**Reproduction Steps**
1. `POST /api/projects/{id}/upload` with CSV/JSON.
2. Confirm no `metrics.json` or `tables/*.tex`/`figures/*.png` generated.

**Minimal Remediation**
- Implement ingestion service that parses uploaded/collected outputs into `metrics.json`.
- Generate `tables/*.tex`, `figures/*.png`, and `results_summary.md` in Part 4.
- Gate Final results on presence of these artifacts.

---

## H. Tests
**Status:** PASS

**Evidence**
- Schema validation test for Part 2 RQ count.【F:backend/tests/test_schemas.py†L1-L21】
- Workflow lock/approve/unlock tests.【F:backend/tests/test_workflow.py†L1-L26】
- Citation verifier error handling test with stubbed HTTP error.【F:backend/tests/test_citations.py†L1-L13】
- Execution plan approval gating test.【F:backend/tests/test_execution.py†L1-L20】

**Reproduction Steps**
1. `make test`

---

# Overall GO/NO-GO Decision
**NO-GO** — core execution, ingestion, and UI requirements are incomplete.
