from enum import StrEnum

from pydantic import BaseModel


class Verdict(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    CITATION_INVALID = "citation_invalid"


class ClaimVerdict(BaseModel):
    claim: str
    source_id: str
    self_confidence: str  # evidence.confidence tier: high/medium/low
    verdict: Verdict
    rationale: str
    judge_confidence: float


class ReportEvalResult(BaseModel):
    our_company: str
    competitor: str
    market: str
    report_type: str
    run_id: str
    verdicts: list[ClaimVerdict]
    metrics: dict


class EvalSummary(BaseModel):
    n_reports: int
    n_claims: int
    aggregate: dict
    per_report_type: dict
    per_report: list[ReportEvalResult]
