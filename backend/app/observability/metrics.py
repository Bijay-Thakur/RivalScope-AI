from typing import Any

from app.core.config import settings


def compute_run_metrics(final_state: dict[str, Any]) -> dict[str, Any]:
    final_report = final_state.get("final_report")
    request = final_state.get("request")
    errors = final_state.get("errors", [])

    warning_count = len(errors)
    if final_report is not None:
        warning_count += len(getattr(final_report, "warnings", []) or [])

    research_mode = settings.research_mode
    if final_report is not None and getattr(final_report, "research_mode", None):
        research_mode = final_report.research_mode

    report_type = None
    if request is not None:
        report_type_value = getattr(request, "report_type", None)
        if report_type_value is not None:
            report_type = getattr(report_type_value, "value", report_type_value)

    return {
        "run_id": final_state.get("run_id"),
        "source_count": len(final_state.get("sources", [])),
        "evidence_count": len(final_state.get("evidence", [])),
        "verified_claim_count": len(final_state.get("verified_claims", [])),
        "warning_count": warning_count,
        "has_final_report": final_report is not None,
        "confidence_score": (
            final_report.confidence_score if final_report is not None else None
        ),
        "research_mode": research_mode,
        "report_type": report_type,
    }
