# Acceptance Checklist — Research Pipeline Studio

Date: 2026-01-08

## Summary
Overall status: **NO-GO** — implementation does not fully satisfy the spec. Multiple core requirements are partial or missing, including UI step editing/rollback, execution safety for SSH/Slurm, and full guardrails.

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
- Results gating: Final step blocks results without `part4/metrics.json` and writes a warning-only Results section.【F:backend/app/workflow.py†L108-L204】
- Verified-only bibliography is written to `artifacts/latex/references.bib`; unverified citations are written to `artifacts/citations/unverified.md` by default.【F:backend/app/workflow.py†L206-L236】
- UI provides citation status view and a toggle for including unverified citations in settings.【F:frontend/src/App.tsx†L33-L337】

**Missing / Partial**
- No Semantic Scholar or arXiv verification options.
- No modal blocking for Final beyond the disabled Run button.

**Reproduction Steps**
1. Run Part 1 with related work candidates; verify `status` fields in output.
2. Run Final step without `metrics.json` and inspect generated LaTeX section for TODOs.

**Minimal Remediation**
- Add verification sources beyond Crossref and merge results.
- Add modal blocking for Final and richer UI warnings for missing evidence.

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
**Status:** PASS

**Evidence**
- Ingestion endpoint parses CSV/JSON, stores uploads, and generates metrics/table/figure/summary artifacts.【F:backend/app/main.py†L303-L320】【F:backend/app/ingestion.py†L14-L113】
- Part 4 UI includes upload + ingest controls and lists generated artifacts.【F:frontend/src/App.tsx†L176-L304】
- Demo CSV included with usage notes.【F:examples/demo-project/README.md†L1-L17】

**Reproduction Steps**
1. `POST /api/projects/{id}/ingest` with a CSV/JSON file.
2. Confirm generated artifacts in `GET /api/projects/{id}/artifacts`.

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
**NO-GO** — core execution and UI requirements are incomplete.
