from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, field_validator

from .citations import CitationVerifier
from .config import PROMPTS_DIR
from .llm import get_client
from .storage import artifacts_dir

STEP_IDS = ["part1", "part2", "part3", "part4", "final"]


class RelatedWorkCandidate(BaseModel):
    title: str
    status: str = "unverified"
    identifiers: Dict[str, str] = Field(default_factory=dict)
    bibtex: str = ""


class Part1Output(BaseModel):
    polished_problem_statement: str
    contribution_hypotheses: List[str]
    paper_type_decision: str
    related_work_candidates: List[RelatedWorkCandidate]
    risks_and_unknowns: List[str]


class ResearchQuestion(BaseModel):
    question: str
    hypothesis: str
    metrics: List[str]
    minimal_experiment: str
    baselines: List[str]
    ablations: List[str]


class Part2Output(BaseModel):
    titles: List[str]
    rqs: List[ResearchQuestion]
    experiment_matrix: Dict[str, Any]

    @field_validator("rqs")
    @classmethod
    def ensure_four_rqs(cls, value: List[ResearchQuestion]) -> List[ResearchQuestion]:
        if len(value) != 4:
            raise ValueError("Exactly 4 research questions are required.")
        return value


class Part3Output(BaseModel):
    section_questions: Dict[str, List[str]]
    claim_evidence_map: Dict[str, Any]
    planned_figures_tables: List[str]


class Part4Output(BaseModel):
    ingestion_summary: str
    metrics_path: str
    tables: List[str]
    figures: List[str]


class FinalOutput(BaseModel):
    latex_project_path: str
    notes: str
    results_allowed: bool = True
    reason: Optional[str] = None


STEP_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "part1": Part1Output,
    "part2": Part2Output,
    "part3": Part3Output,
    "part4": Part4Output,
    "final": FinalOutput,
}


class PromptTemplate(BaseModel):
    version: str
    system: str
    user: str


class PromptLoader:
    def load(self, step_id: str) -> PromptTemplate:
        prompt_path = PROMPTS_DIR / f"{step_id}.json"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found for {step_id}")
        data = json.loads(prompt_path.read_text(encoding="utf-8"))
        return PromptTemplate(**data)


def run_step(
    project_id: int,
    step_id: str,
    inputs: Dict[str, Any],
    provider: str,
    model: str,
    temperature: float,
    max_tokens: int,
    project_settings: Optional[Dict[str, Any]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if step_id not in STEP_IDS:
        raise ValueError("Unknown step")
    prompt = PromptLoader().load(step_id)
    response_schema = STEP_SCHEMAS[step_id]
    if step_id == "final":
        metrics_file = artifacts_dir(project_id) / "part4" / "metrics.json"
        if not metrics_file.exists():
            output = {
                "latex_project_path": str(artifacts_dir(project_id) / "latex"),
                "notes": "Results blocked: metrics.json not found. Run Part 4 ingestion first.",
                "results_allowed": False,
                "reason": "Results blocked: metrics.json not found. Run Part 4 ingestion first.",
            }
            _write_latex_project(
                project_id,
                results_allowed=False,
                warning="Results blocked: metrics.json not found. Run Part 4 ingestion first.",
            )
            _write_bibliography(project_id, citations or [], project_settings or {})
            return {"output": output, "prompt_version": prompt.version}

    client = get_client(provider)
    messages = [
        {"role": "system", "content": prompt.system},
        {"role": "user", "content": prompt.user.format(**inputs)},
    ]
    output = client.generate(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_schema=response_schema,
    )
    if step_id == "part1":
        verifier = CitationVerifier()
        verified_candidates = []
        for candidate in output.get("related_work_candidates", []):
            title = candidate.get("title", "")
            verification = verifier.verify(title)
            merged = {**candidate, **verification}
            verified_candidates.append(merged)
        output["related_work_candidates"] = verified_candidates
    if step_id == "final":
        output["results_allowed"] = True
        output["reason"] = None
        _write_latex_project(project_id, results_allowed=True, warning=None)
        _write_bibliography(project_id, citations or [], project_settings or {})
        output["latex_project_path"] = str(artifacts_dir(project_id) / "latex")
    return {"output": output, "prompt_version": prompt.version}


def _write_latex_project(
    project_id: int, results_allowed: bool, warning: Optional[str]
) -> None:
    latex_root = artifacts_dir(project_id) / "latex"
    sections_dir = latex_root / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    main_tex = latex_root / "main.tex"
    main_tex.write_text(
        "\\\\documentclass{article}\n"
        "\\\\usepackage{booktabs}\n"
        "\\\\begin{document}\n"
        "\\\\input{sections/abstract}\n"
        "\\\\input{sections/introduction}\n"
        "\\\\input{sections/method}\n"
        "\\\\input{sections/results}\n"
        "\\\\input{sections/discussion}\n"
        "\\\\input{sections/related_work}\n"
        "\\\\end{document}\n",
        encoding="utf-8",
    )
    (sections_dir / "abstract.tex").write_text("% TODO: Abstract\n", encoding="utf-8")
    (sections_dir / "introduction.tex").write_text("% TODO: Introduction\n", encoding="utf-8")
    (sections_dir / "method.tex").write_text("% TODO: Method\n", encoding="utf-8")
    if results_allowed:
        results_body = "% TODO: Results\n"
    else:
        banner = warning or "Results blocked: metrics.json not found."
        results_body = (
            "% WARNING: Results section is blocked.\n"
            f"% {banner}\n"
            "% TODO: Run Part 4 ingestion to enable results.\n"
        )
    (sections_dir / "results.tex").write_text(results_body, encoding="utf-8")
    (sections_dir / "discussion.tex").write_text("% TODO: Discussion\n", encoding="utf-8")
    (sections_dir / "related_work.tex").write_text("% TODO: Related Work\n", encoding="utf-8")


def _write_bibliography(
    project_id: int,
    citations: List[Dict[str, Any]],
    project_settings: Dict[str, Any],
) -> None:
    latex_root = artifacts_dir(project_id) / "latex"
    citations_root = artifacts_dir(project_id) / "citations"
    citations_root.mkdir(parents=True, exist_ok=True)
    include_unverified = project_settings.get("include_unverified_citations", False)
    verified_entries = []
    unverified_entries = []
    for citation in citations:
        status = citation.get("status", "unverified")
        title = citation.get("title", "Untitled")
        bibtex = citation.get("bibtex", "")
        if status == "verified" and bibtex:
            verified_entries.append(bibtex)
        else:
            unverified_entries.append(f"- {title} (UNVERIFIED)")
            if include_unverified and bibtex:
                verified_entries.append(f"% UNVERIFIED\n{bibtex}")
    (latex_root / "references.bib").write_text(
        "\n".join(verified_entries) + "\n", encoding="utf-8"
    )
    (citations_root / "unverified.md").write_text(
        "\n".join(unverified_entries) + "\n", encoding="utf-8"
    )


def ensure_metrics_artifacts(project_id: int) -> Path:
    metrics_path = artifacts_dir(project_id) / "metrics.json"
    if not metrics_path.exists():
        metrics_path.write_text("{}", encoding="utf-8")
    return metrics_path
