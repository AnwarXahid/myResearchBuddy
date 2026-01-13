from __future__ import annotations

import csv
import json
from datetime import datetime
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .storage import artifacts_dir


def _coerce_value(value: str) -> float | str:
    try:
        return float(value)
    except (ValueError, TypeError):
        return str(value)


def _parse_csv(content: str) -> Dict[str, float | str]:
    reader = csv.reader(content.splitlines())
    rows = [row for row in reader if row]
    if not rows:
        raise ValueError("Empty CSV")
    header = [cell.strip() for cell in rows[0]]
    if len(header) == 2 and header[0].lower() == "metric" and header[1].lower() == "value":
        metrics: Dict[str, float | str] = {}
        for row in rows[1:]:
            if len(row) < 2:
                continue
            metrics[row[0].strip()] = _coerce_value(row[1].strip())
        return metrics
    if len(rows) < 2:
        raise ValueError("CSV must include a header and a value row")
    values = rows[1]
    metrics = {}
    for key, value in zip(header, values):
        metrics[key.strip()] = _coerce_value(value.strip())
    return metrics


def _parse_json(content: str) -> Dict[str, float | str]:
    data = json.loads(content)
    if isinstance(data, dict) and "metrics" in data and isinstance(data["metrics"], dict):
        return data["metrics"]
    if isinstance(data, dict):
        return data
    raise ValueError("JSON must be an object with metrics")


def _render_table(metrics: Dict[str, float | str]) -> str:
    lines = [
        "\\begin{tabular}{lr}",
        "\\toprule",
        "Metric & Value \\\\",
        "\\midrule",
    ]
    for key, value in metrics.items():
        lines.append(f"{key} & {value} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    return "\n".join(lines)


def _render_results_summary(metrics: Dict[str, float | str]) -> str:
    keys = list(metrics.keys())
    bullet_count = min(6, max(3, len(keys)))
    selected = keys[:bullet_count]
    bullets = [f"- {key}: {metrics[key]}" for key in selected]
    return "\n".join(bullets)


def ingest_metrics(project_id: int, filename: str, content: bytes, label: str | None) -> List[str]:
    text = content.decode("utf-8")
    if filename.lower().endswith(".csv"):
        metrics = _parse_csv(text)
    elif filename.lower().endswith(".json"):
        metrics = _parse_json(text)
    else:
        raise ValueError("Unsupported file type")

    base = artifacts_dir(project_id) / "part4"
    uploads_dir = base / "uploads"
    tables_dir = base / "tables"
    figures_dir = base / "figures"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    upload_path = uploads_dir / filename
    upload_path.write_bytes(content)

    metrics_path = base / "metrics.json"
    payload = {
        "metrics": metrics,
        "source_files": [str(upload_path.relative_to(artifacts_dir(project_id)))],
        "generated_at": datetime.utcnow().isoformat(),
        "label": label,
    }
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    table_path = tables_dir / "metrics_table.tex"
    table_path.write_text(_render_table(metrics), encoding="utf-8")

    figure_path = figures_dir / "metrics.png"
    plt.figure(figsize=(6, 3))
    plt.bar(list(metrics.keys()), [float(v) if isinstance(v, (int, float)) else 0 for v in metrics.values()])
    plt.ylabel("value")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(figure_path)
    plt.close()

    summary_path = base / "results_summary.md"
    summary_path.write_text(_render_results_summary(metrics), encoding="utf-8")

    return [
        str(metrics_path.relative_to(artifacts_dir(project_id))),
        str(table_path.relative_to(artifacts_dir(project_id))),
        str(figure_path.relative_to(artifacts_dir(project_id))),
        str(summary_path.relative_to(artifacts_dir(project_id))),
        str(upload_path.relative_to(artifacts_dir(project_id))),
    ]
