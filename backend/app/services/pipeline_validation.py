"""Deterministic source-ID allowlists + comparison / plan business rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas.report import (
    ComparisonMatrix,
    EvidenceItem,
    FeatureComparisonRow,
    Source,
    VerifiedClaim,
)
from app.schemas.research import ResearchTask

_NOT_FOUND = "not found in available sources"
_ALLOWED_ADVANTAGE = frozenset({"our", "competitor", "parity", "unclear"})
_ALLOWED_TRACKS = frozenset(
    {"company_profile", "product_features", "pricing", "recent_news"}
)
_ALLOWED_FC_STATUS = frozenset({"verified", "weakly_supported", "unsupported"})


@dataclass(frozen=True)
class SourceAllowlists:
    all_ids: frozenset[str]
    our_ids: frozenset[str]
    competitor_ids: frozenset[str]
    untagged_ids: frozenset[str]


def build_source_allowlists(
    sources: list[Source],
    our_company: str,
    competitor: str,
) -> SourceAllowlists:
    all_ids = frozenset(s.id for s in sources)
    our = frozenset(s.id for s in sources if s.company == our_company)
    rival = frozenset(s.id for s in sources if s.company == competitor)
    untagged = frozenset(
        s.id for s in sources if s.company not in {our_company, competitor}
    )
    return SourceAllowlists(
        all_ids=all_ids, our_ids=our, competitor_ids=rival, untagged_ids=untagged
    )


def filter_known_source_ids(
    ids: list[str], allowed: frozenset[str]
) -> list[str]:
    """Keep order, drop unknown + duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for sid in ids:
        if sid in allowed and sid not in seen:
            out.append(sid)
            seen.add(sid)
    return out


@dataclass
class ValidationIssue:
    code: str
    message: str


@dataclass
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, code: str, message: str) -> None:
        self.issues.append(ValidationIssue(code, message))
        self.ok = False


def _cell_missing(value: str) -> bool:
    v = (value or "").strip().lower()
    return (not v) or (_NOT_FOUND in v)


def pricing_values_incompatible(our_value: str, competitor_value: str) -> bool:
    """Conservative check: different currency symbols or month vs year basis."""
    a = (our_value or "").lower()
    b = (competitor_value or "").lower()
    if _cell_missing(a) or _cell_missing(b):
        return False
    if ("$" in a or "usd" in a) and ("€" in b or "eur" in b):
        return True
    if ("€" in a or "eur" in a) and ("$" in b or "usd" in b):
        return True
    month_a = "/mo" in a or "per month" in a or "/month" in a
    year_a = "/yr" in a or "per year" in a or "/year" in a or "annual" in a
    month_b = "/mo" in b or "per month" in b or "/month" in b
    year_b = "/yr" in b or "per year" in b or "/year" in b or "annual" in b
    return (month_a and year_b) or (year_a and month_b)


def validate_comparison_matrix(
    matrix: ComparisonMatrix,
    allowlists: SourceAllowlists,
    *,
    min_rows: int = 5,
    max_rows: int = 8,
    strict_row_count: bool = False,
) -> tuple[ComparisonMatrix, ValidationResult]:
    """Validate + coerce comparison matrix. Always returns a usable matrix."""
    result = ValidationResult(ok=True)
    rows_in = list(matrix.rows)
    if strict_row_count and not (min_rows <= len(rows_in) <= max_rows):
        result.add(
            "row_count",
            f"expected {min_rows}-{max_rows} rows, got {len(rows_in)}",
        )

    dims_seen: set[str] = set()
    fixed_rows: list[FeatureComparisonRow] = []
    for row in rows_in:
        dim = (row.dimension or "").strip() or "Unspecified dimension"
        dim_key = dim.lower()
        if dim_key in dims_seen:
            result.add("duplicate_dimension", f"duplicate dimension: {dim}")
            continue
        dims_seen.add(dim_key)

        adv = (row.advantage or "unclear").strip().lower()
        if adv not in _ALLOWED_ADVANTAGE:
            result.add("bad_advantage", f"invalid advantage '{row.advantage}'")
            adv = "unclear"

        our_ids = filter_known_source_ids(row.our_source_ids, allowlists.all_ids)
        rival_ids = filter_known_source_ids(
            row.competitor_source_ids, allowlists.all_ids
        )

        # Company ownership: drop IDs that belong exclusively to the other side.
        if allowlists.our_ids or allowlists.competitor_ids:
            our_ids = [
                i
                for i in our_ids
                if i in allowlists.our_ids or i in allowlists.untagged_ids
            ]
            rival_ids = [
                i
                for i in rival_ids
                if i in allowlists.competitor_ids or i in allowlists.untagged_ids
            ]

        our_missing = _cell_missing(row.our_value) or not our_ids
        rival_missing = _cell_missing(row.competitor_value) or not rival_ids

        if our_missing or rival_missing:
            if adv in {"our", "competitor", "parity"}:
                result.add(
                    "advantage_without_both_sides",
                    f"dimension '{dim}': advantage={adv} with missing side → unclear",
                )
                adv = "unclear"

        dim_l = dim.lower()
        if "pric" in dim_l and pricing_values_incompatible(
            row.our_value, row.competitor_value
        ):
            if adv in {"our", "competitor", "parity"}:
                result.add(
                    "incompatible_pricing",
                    f"dimension '{dim}': incompatible pricing units/currency → unclear",
                )
                adv = "unclear"

        fixed_rows.append(
            FeatureComparisonRow(
                dimension=dim,
                our_value=row.our_value
                if not _cell_missing(row.our_value)
                else "Not found in available sources.",
                competitor_value=row.competitor_value
                if not _cell_missing(row.competitor_value)
                else "Not found in available sources.",
                our_source_ids=our_ids,
                competitor_source_ids=rival_ids,
                advantage=adv,
            )
        )

    if not fixed_rows:
        result.add("no_rows", "comparison matrix has no valid rows")
        fixed_rows = [
            FeatureComparisonRow(
                dimension="Overall positioning",
                our_value="Not found in available sources.",
                competitor_value="Not found in available sources.",
                our_source_ids=[],
                competitor_source_ids=[],
                advantage="unclear",
            )
        ]

    # Soft pad/truncate toward 5–8 when we have evidence-backed rows but LLM under/over-shot
    if len(fixed_rows) > max_rows:
        result.add("row_count_trim", f"trimmed {len(fixed_rows)} → {max_rows} rows")
        fixed_rows = fixed_rows[:max_rows]

    out = ComparisonMatrix(
        rows=fixed_rows,
        pricing_comparison=str(matrix.pricing_comparison or "").strip()
        or "Not found in available sources.",
        positioning_gap=str(matrix.positioning_gap or "").strip()
        or "Not found in available sources.",
        summary=str(matrix.summary or "").strip() or "Comparison summary unavailable.",
    )
    # ok stays False if we recorded issues that aren't mere coercions
    hard = {
        "no_rows",
        "duplicate_dimension",
        "bad_advantage",
        "advantage_without_both_sides",
    }
    if any(i.code in hard for i in result.issues):
        result.ok = False
    elif not result.issues:
        result.ok = True
    return out, result


def normalize_fact_checker_results(
    batch: list[EvidenceItem],
    raw_items: list[dict],
    allowlists: SourceAllowlists,
) -> list[VerifiedClaim]:
    """Enforce 1:1 with input batch: preserve claim text/order; scrub source IDs."""
    by_id: dict[str, dict] = {}
    by_claim: dict[str, dict] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or item.get("claim_id") or "").strip()
        claim = str(item.get("claim") or item.get("claim_text") or "").strip()
        if cid:
            by_id[cid] = item
        if claim:
            by_claim[claim.lower()] = item

    results: list[VerifiedClaim] = []
    for ev in batch:
        raw = by_id.get(ev.id) or by_claim.get(ev.claim.strip().lower()) or {}
        status = str(
            raw.get("verification_status")
            or raw.get("status")
            or "weakly_supported"
        ).strip().lower()
        if status not in _ALLOWED_FC_STATUS:
            status = "weakly_supported"

        raw_ids = raw.get("source_ids") or raw.get("sourceIds") or [ev.source_id]
        if not isinstance(raw_ids, list):
            raw_ids = [ev.source_id]
        ids = filter_known_source_ids([str(x) for x in raw_ids], allowlists.all_ids)
        if not ids and ev.source_id in allowlists.all_ids:
            ids = [ev.source_id]
        if status == "verified" and not ids:
            status = "weakly_supported"

        try:
            conf = float(raw.get("confidence_score", raw.get("confidenceScore", 0.5)))
        except (TypeError, ValueError):
            conf = 0.5
        conf = max(0.0, min(1.0, conf))

        results.append(
            VerifiedClaim(
                id=ev.id,
                claim=ev.claim,
                source_ids=ids,
                verification_status=status,
                confidence_score=conf,
            )
        )
    return results


def _norm_query(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip().lower())


def validate_research_plan(
    tasks: list[ResearchTask],
    *,
    strict: bool = True,
) -> ValidationResult:
    """Programmatic planner gates (7–9 tasks, track coverage, no duplicate queries).

    ``ResearchTask.objective`` is the query text (repository convention).
    """
    result = ValidationResult(ok=True)
    n = len(tasks)
    if strict:
        if not (7 <= n <= 9):
            result.add("task_count", f"expected 7-9 tasks, got {n}")
    elif n < 4:
        result.add("task_count", f"expected ≥4 tasks, got {n}")
    elif n > 9:
        result.add("task_count", f"expected ≤9 tasks, got {n}")

    counts: dict[str, int] = {t: 0 for t in _ALLOWED_TRACKS}
    queries: list[str] = []
    for task in tasks:
        if task.track not in _ALLOWED_TRACKS:
            result.add("unknown_track", f"unknown track '{task.track}'")
            continue
        counts[task.track] += 1
        q = (getattr(task, "objective", None) or "").strip()
        if not q:
            result.add("empty_query", f"empty objective on task {task.id}")
            continue
        nq = _norm_query(q)
        if nq in queries:
            result.add("duplicate_query", f"duplicate normalized query: {nq[:80]}")
        queries.append(nq)

    if strict:
        if not (1 <= counts["company_profile"] <= 2):
            result.add(
                "track_coverage",
                f"company_profile requires 1-2 tasks, got {counts['company_profile']}",
            )
        if not (2 <= counts["product_features"] <= 3):
            result.add(
                "track_coverage",
                f"product_features requires 2-3 tasks, got {counts['product_features']}",
            )
        if not (1 <= counts["pricing"] <= 2):
            result.add(
                "track_coverage",
                f"pricing requires 1-2 tasks, got {counts['pricing']}",
            )
        if counts["recent_news"] != 2:
            result.add(
                "track_coverage",
                f"recent_news requires exactly 2 tasks, got {counts['recent_news']}",
            )
    else:
        for track in _ALLOWED_TRACKS:
            if counts[track] < 1:
                result.add("track_coverage", f"{track} requires ≥1 task")

    if not result.issues:
        result.ok = True
    return result
