"""Manual live-research smoke test.

Run from the backend directory:

    python scripts/manual_live_research_test.py

Requires RESEARCH_MODE=real and valid API keys in .env (or the environment).
This file is intentionally excluded from pytest collection.
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

# Force UTF-8 stdout so box-drawing characters work on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ---------------------------------------------------------------------------
# Ensure the backend package is importable when run directly.
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Load .env before importing settings so pydantic-settings picks up the keys.
try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass  # python-dotenv may not be installed; rely on OS environment


def _check_prerequisites() -> None:
    from app.core.config import settings

    if not settings.is_real_research_enabled:
        print(
            "\n[ERROR] RESEARCH_MODE is not 'real'.\n"
            "        Set RESEARCH_MODE=real in your .env file or environment,\n"
            "        then re-run this script.\n"
        )
        sys.exit(1)

    missing: list[str] = []
    if not settings.has_tavily_key:
        missing.append("TAVILY_API_KEY")
    if not (settings.has_groq_key or settings.has_gemini_key):
        missing.append("GROQ_API_KEY or GOOGLE_API_KEY or GEMINI_API_KEY (at least one)")

    if missing:
        print(
            "\n[ERROR] Missing required API key(s):\n"
            + "".join(f"  - {k}\n" for k in missing)
            + "\n        Set them in backend/.env and re-run.\n"
        )
        sys.exit(1)

    print(
        f"[OK] research_mode=real | "
        f"tavily={'set' if settings.has_tavily_key else 'missing'} | "
        f"groq={'set' if settings.has_groq_key else 'missing'} | "
        f"gemini={'set' if settings.has_gemini_key else 'missing'}"
    )


def _print_section(title: str, value: object) -> None:
    bar = "─" * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)
    if isinstance(value, list):
        for i, item in enumerate(value, 1):
            print(f"  {i}. {item}")
    else:
        print(f"  {value}")


async def _run(request):
    from app.graph.workflow import run_research_graph

    return await run_research_graph(request)


def main() -> None:
    _check_prerequisites()

    from app.core.logging import setup_logging
    from app.schemas.research import ReportType, ResearchRequest

    setup_logging()

    request = ResearchRequest(
        our_company="ClickUp",
        competitor="Notion",
        market="project management and docs",
        report_type=ReportType.SALES_BATTLECARD,
    )

    print(f"\n[RUN] {request.our_company} vs {request.competitor} in {request.market}")
    print("      Calling run_research_graph — this may take 30–60 seconds...\n")

    try:
        state = asyncio.run(_run(request))
    except Exception as exc:
        print(f"\n[FATAL] Research graph failed: {exc}")
        sys.exit(1)

    report = state.get("final_report")
    if report is None:
        print("\n[FATAL] Graph completed but final_report is None.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------
    print("\n" + "═" * 62)
    print("  LIVE RESEARCH RESULTS")
    print("═" * 62)
    print(f"  run_id          : {state['run_id']}")
    print(f"  sources         : {len(state['sources'])}")
    print(f"  evidence items  : {len(state['evidence'])}")
    print(f"  verified claims : {len(state['verified_claims'])}")
    print(f"  confidence score: {report.confidence_score:.0f}/100")
    print(f"  research_mode   : {report.research_mode or 'n/a'}")
    print(f"  generated_at    : {report.generated_at or 'n/a'}")

    if state.get("errors"):
        print(f"\n  warnings ({len(state['errors'])}):")
        for w in state["errors"]:
            print(f"    ⚠  {w}")

    _print_section("Company Snapshot", report.company_snapshot)
    _print_section("Product Positioning", report.product_positioning)
    _print_section("Feature Comparison", report.feature_comparison)
    _print_section("Pricing Intelligence", report.pricing_intelligence)
    _print_section("Recent Moves", report.recent_moves)
    _print_section("Strengths", report.strengths)
    _print_section("Weaknesses", report.weaknesses)
    _print_section("Talk Tracks", report.sales_battlecard.talk_tracks)
    _print_section("Objection Handling", report.sales_battlecard.objection_handling)
    _print_section("Landmines", report.sales_battlecard.landmines)

    # ------------------------------------------------------------------
    # Save full report to logs/
    # ------------------------------------------------------------------
    logs_dir = BACKEND_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_path = logs_dir / "manual_live_report.json"

    report_dict = report.model_dump(by_alias=True, mode="json")
    output_path.write_text(
        json.dumps(report_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[SAVED] Full report written to {output_path.relative_to(BACKEND_DIR)}\n")


if __name__ == "__main__":
    main()
