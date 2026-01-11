# Design Notes

- Workflow steps are backed by SQLModel tables and versioned StepRun records.
- Each step pulls a prompt template from `/prompts` and validates responses against Pydantic schemas.
- Execution plans are stored and must be explicitly approved before any run.
- Artifacts are stored per project in `data/projects/project_<id>/artifacts`.
