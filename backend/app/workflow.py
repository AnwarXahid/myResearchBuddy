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
) -> Dict[str, Any]:
    if step_id not in STEP_IDS:
        raise ValueError("Unknown step")
    prompt = PromptLoader().load(step_id)
    client = get_client(provider)
    messages = [
        {"role": "system", "content": prompt.system},
        {"role": "user", "content": prompt.user.format(**inputs)},
    ]
    response_schema = STEP_SCHEMAS[step_id]
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
        metrics_file = artifacts_dir(project_id) / "metrics.json"
        latex_root = artifacts_dir(project_id) / "latex"
        sections_dir = latex_root / "sections"
        sections_dir.mkdir(parents=True, exist_ok=True)
        results_todo = ""
        if not metrics_file.exists():
            results_todo = "\\n% TODO: Results section blocked; metrics.json missing.\\n"
            output["notes"] += "\nTODO: Results section blocked; metrics.json missing."
        main_tex = latex_root / "main.tex"
        main_tex.write_text(
            "\\\\documentclass{article}\n"
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
        (sections_dir / "introduction.tex").write_text(
            "% TODO: Introduction\n", encoding="utf-8"
        )
        (sections_dir / "method.tex").write_text("% TODO: Method\n", encoding="utf-8")
        (sections_dir / "results.tex").write_text(
            f"% TODO: Results{results_todo}\n",
            encoding="utf-8",
        )
        (sections_dir / "discussion.tex").write_text("% TODO: Discussion\n", encoding="utf-8")
        (sections_dir / "related_work.tex").write_text(
            "% TODO: Related Work\n", encoding="utf-8"
        )
        (latex_root / "references.bib").write_text(
            "% Verified references only\n", encoding="utf-8"
        )
        output["latex_project_path"] = str(latex_root)
    return {"output": output, "prompt_version": prompt.version}


def ensure_metrics_artifacts(project_id: int) -> Path:
    metrics_path = artifacts_dir(project_id) / "metrics.json"
    if not metrics_path.exists():
        metrics_path.write_text("{}", encoding="utf-8")
    return metrics_path
