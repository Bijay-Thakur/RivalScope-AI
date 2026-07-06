"""Grounding eval harness — measures citation grounding rate over a gold set.

Run from backend/:
    python -m evals.harness [--dataset PATH] [--limit N] [--out DIR]

Requires live TAVILY + GOOGLE/GEMINI keys (calls run_research_graph directly, in-process).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.graph.workflow import run_research_graph
from app.observability.tracing import traceable
from app.schemas.research import ReportType, ResearchRequest
from evals.judge import judge_claims
from evals.metrics import aggregate, report_metrics
from evals.schemas import ClaimVerdict, EvalSummary, ReportEvalResult, Verdict

logger = get_logger(__name__)

_EVALS_DIR = Path(__file__).resolve().parent
_DEFAULT_DATASET = _EVALS_DIR / "datasets" / "company_pairs.json"
_DEFAULT_OUT = _EVALS_DIR / "results"


def _require_keys() -> None:
    missing = []
    if not settings.has_tavily_key:
        missing.append("TAVILY_API_KEY")
    if not settings.has_gemini_key:
        missing.append("GOOGLE_API_KEY or GEMINI_API_KEY")
    if missing:
        print(f"[ERROR] eval needs {' + '.join(missing)} set. Aborting.")
        sys.exit(1)


def _load_dataset(path: Path, limit: int | None) -> list[ResearchRequest]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        ResearchRequest(
            our_company=c["ourCompany"],
            competitor=c["competitor"],
            market=c["market"],
            report_type=ReportType(c["reportType"]),
        )
        for c in raw
    ]
    return cases[:limit] if limit else cases


async def _eval_single_report(
    request: ResearchRequest,
    judge_model: str,
    max_concurrency: int,
) -> ReportEvalResult:
    state = await run_research_graph(request)
    report = state.get("final_report")
    run_id = state["run_id"]

    if report is None:
        return ReportEvalResult(
            our_company=request.our_company,
            competitor=request.competitor,
            market=request.market,
            report_type=request.report_type.value,
            run_id=run_id,
            verdicts=[],
            metrics=report_metrics([]),
        )

    source_map = {s.id: s for s in report.sources}
    verdicts: list[ClaimVerdict | None] = [None] * len(report.evidence)
    judge_idx: list[int] = []
    judge_items: list[dict] = []

    for i, item in enumerate(report.evidence):
        src = source_map.get(item.source_id)
        if src is None:
            verdicts[i] = ClaimVerdict(
                claim=item.claim,
                source_id=item.source_id,
                self_confidence=item.confidence,
                verdict=Verdict.CITATION_INVALID,
                rationale="source_id not found among report sources",
                judge_confidence=1.0,
            )
            continue
        judge_idx.append(i)
        judge_items.append(
            {
                "claim": item.claim,
                "source_title": src.title,
                "source_url": src.url,
                "source_text": item.raw_text or src.snippet or "",
            }
        )

    judged = await judge_claims(judge_items, model=judge_model, max_concurrency=max_concurrency)
    for idx, (verdict, rationale, judge_confidence) in zip(judge_idx, judged):
        item = report.evidence[idx]
        verdicts[idx] = ClaimVerdict(
            claim=item.claim,
            source_id=item.source_id,
            self_confidence=item.confidence,
            verdict=verdict,
            rationale=rationale,
            judge_confidence=judge_confidence,
        )

    final_verdicts = [v for v in verdicts if v is not None]
    return ReportEvalResult(
        our_company=request.our_company,
        competitor=request.competitor,
        market=request.market,
        report_type=request.report_type.value,
        run_id=run_id,
        verdicts=final_verdicts,
        metrics=report_metrics(final_verdicts),
    )


@traceable(run_type="chain", name="eval_harness_run")
async def run_eval(
    dataset_path: Path,
    limit: int | None,
    out_dir: Path,
    case_concurrency: int = 2,
) -> EvalSummary:
    cases = _load_dataset(dataset_path, limit)
    judge_model = settings.judge_model
    judge_concurrency = settings.eval_max_concurrency
    semaphore = asyncio.Semaphore(case_concurrency)

    async def _bounded(request: ResearchRequest) -> ReportEvalResult:
        async with semaphore:
            return await _eval_single_report(request, judge_model, judge_concurrency)

    results = list(await asyncio.gather(*(_bounded(c) for c in cases)))
    agg = aggregate(results)

    summary = EvalSummary(
        n_reports=len(results),
        n_claims=sum(len(r.verdicts) for r in results),
        aggregate=agg["aggregate"],
        per_report_type=agg["per_report_type"],
        per_report=results,
    )

    _write_results(summary, out_dir)
    _print_markdown(summary)
    return summary


def _write_results(summary: EvalSummary, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = summary.model_dump_json(indent=2)
    (out_dir / f"eval_{ts}.json").write_text(payload, encoding="utf-8")
    (out_dir / "latest_summary.json").write_text(payload, encoding="utf-8")


def _print_markdown(summary: EvalSummary) -> None:
    agg = summary.aggregate
    print("\n## Grounding Eval Summary\n")
    print(f"- reports: {summary.n_reports}  |  claims: {summary.n_claims}")
    print(f"- **grounding rate (strict)**: {agg['grounding_rate_strict']:.1%}")
    print(f"- grounding rate (lenient): {agg['grounding_rate_lenient']:.1%}")
    print(f"- **hallucination rate**: {agg['hallucination_rate']:.1%}")
    print(f"- unsupported rate: {agg['unsupported_rate']:.1%}")
    print(f"- citation validity: {agg['citation_validity']:.1%}")
    print(f"- calibration (strict grounding by self-confidence): {agg['calibration']}")

    print("\n| report_type | claims | grounding (strict) | hallucination |")
    print("|---|---|---|---|")
    for rt, m in summary.per_report_type.items():
        print(f"| {rt} | {m['total_claims']} | {m['grounding_rate_strict']:.1%} | {m['hallucination_rate']:.1%} |")
    print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RivalScope grounding eval harness")
    parser.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    _require_keys()
    args = _parse_args()
    asyncio.run(run_eval(args.dataset, args.limit, args.out))


if __name__ == "__main__":
    main()
