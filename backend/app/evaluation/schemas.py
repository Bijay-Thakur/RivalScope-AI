from enum import StrEnum

from pydantic import BaseModel, Field


class BenchmarkTask(BaseModel):
    id: str
    our_company: str
    competitor: str
    market: str
    report_type: str
    expected_sections: list[str]
    expected_source_types: list[str]
    expected_facts: list[str]
    notes: str | None = None


# --- Grounding (ported from evals/) ---------------------------------------

class Verdict(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    CITATION_INVALID = "citation_invalid"
    ERROR = "error"  # judge never produced a real verdict (API/parse failure)


class ClaimVerdict(BaseModel):
    claim: str
    source_id: str
    self_confidence: str  # evidence.confidence tier: high/medium/low
    verdict: Verdict
    rationale: str
    judge_confidence: float


class TaskScore(BaseModel):
    task_id: str
    task_completion: float
    section_coverage: float
    source_coverage: float
    citation_integrity: float
    evidence_count: int
    source_count: int
    latency_seconds: float
    warnings_count: int
    overall_score: float
    failure_notes: list[str]

    # Comparison quality (deterministic — computed in every mode)
    comparison_two_sidedness: float | None = None
    comparison_citation_validity: float | None = None
    advantage_distribution: dict[str, int] = Field(default_factory=dict)

    # Grounding (LLM-judge — populated only in --mode full)
    grounding_rate: float | None = None  # null if n_judged_ok==0
    hallucination_rate: float | None = None
    comparison_grounding: float | None = None
    n_claims_total: int | None = None
    n_judged_ok: int | None = None
    n_judge_errors: int | None = None
    n_citation_invalid: int | None = None


class ExperimentResult(BaseModel):
    experiment_name: str
    model_provider: str
    research_mode: str
    eval_mode: str = "structural"
    judge_model: str | None = None
    langsmith_tracing: bool = False
    langsmith_project: str | None = None
    total_tasks: int
    average_score: float
    average_latency_seconds: float
    average_source_count: float
    # headline averages (None when not computed for the mode)
    avg_comparison_two_sidedness: float | None = None
    avg_comparison_citation_validity: float | None = None
    avg_grounding_rate: float | None = None
    avg_hallucination_rate: float | None = None
    avg_comparison_grounding: float | None = None
    # judge observability (full mode only; 0/None in structural)
    n_claims_total: int = 0
    n_judged_ok: int = 0
    n_judge_errors: int = 0
    n_citation_invalid: int = 0
    grounding_unreliable: bool = False
    task_scores: list[TaskScore]
