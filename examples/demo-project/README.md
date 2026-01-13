# Demo Project

This folder contains demo artifacts for Research Pipeline Studio.

- `part1.json` - sample Part 1 output
- `metrics.json` - sample metrics for results gating
- `metrics.csv` - sample metrics upload for ingestion
- `latex/main.tex` - sample LaTeX export

## Ingestion Demo

1. Open the app and select the demo project.
2. Navigate to Part 4.
3. Upload `examples/demo-project/metrics.csv` and click **Ingest**.
4. Confirm generated artifacts appear in the artifacts list:
   - `part4/metrics.json`
   - `part4/tables/metrics_table.tex`
   - `part4/figures/metrics.png`
   - `part4/results_summary.md`
