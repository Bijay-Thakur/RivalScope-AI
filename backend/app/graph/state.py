import operator
from typing import Annotated, TypedDict

from app.schemas.events import ProgressEvent
from app.schemas.report import (
    CompetitorReport,
    EvidenceItem,
    Source,
    VerifiedClaim,
)
from app.schemas.research import ResearchRequest, ResearchTask


def _take_last(left: str, right: str) -> str:
    return right


class RivalScopeState(TypedDict):
    run_id: str
    request: ResearchRequest
    current_step: Annotated[str, _take_last]
    progress_events: Annotated[list[ProgressEvent], operator.add]
    research_plan: list[ResearchTask]
    evidence: Annotated[list[EvidenceItem], operator.add]
    sources: Annotated[list[Source], operator.add]
    verified_claims: list[VerifiedClaim]
    final_report: CompetitorReport | None
    errors: list[str]
