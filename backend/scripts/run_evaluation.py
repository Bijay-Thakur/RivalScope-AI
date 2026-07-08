"""Run benchmark evaluation and write experiment artifacts.

Run from the backend directory:

    python scripts/run_evaluation.py --experiment-name phase4_mock_baseline --max-tasks 5

Loads settings from backend/.env (or the environment). Mock mode requires no API keys.
Real mode consumes Groq and Tavily credits.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
from pathlib import Path

# Force UTF-8 stdout so output is readable on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run RivalScope benchmark evaluation and write results."
    )
    parser.add_argument(
        "--experiment-name",
        "--experiment",
        dest="experiment_name",
        default="phase4_baseline",
        help="Name for this evaluation run (default: phase4_baseline)",
    )
    parser.add_argument(
        "--max-tasks",
        "--limit",
        dest="max_tasks",
        type=int,
        default=5,
        help="Limit the number of benchmark tasks to run (default: 5)",
    )
    parser.add_argument(
        "--mode",
        choices=("structural", "full"),
        default="structural",
        help="structural = deterministic only (offline, free); full = + LLM-judge grounding",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to benchmark tasks JSON (default: app/evaluation/benchmark_tasks.json)",
    )
    parser.add_argument(
        "--out",
        default="backend/eval_results",
        help="Output directory for results (default: backend/eval_results)",
    )
    return parser.parse_args()


def _print_mode_notice() -> None:
    from app.core.config import settings

    if settings.langsmith_tracing:
        print(
            f"[INFO] LangSmith tracing ON — project={settings.langsmith_project!r}. "
            "Traces will appear at https://smith.langchain.com"
        )
    else:
        print(
            "[INFO] LangSmith tracing OFF — set LANGSMITH_TRACING=true in backend/.env "
            "to export traces."
        )

    if settings.is_real_research_enabled:
        print(
            "[NOTICE] RESEARCH_MODE=real — this evaluation will consume "
            "Groq and Tavily API credits."
        )
    else:
        print("[INFO] RESEARCH_MODE=mock — no external API keys required.")


async def _run(args: argparse.Namespace):
    from app.evaluation.report_writer import write_experiment_results
    from app.evaluation.runner import run_evaluation

    result = await run_evaluation(
        experiment_name=args.experiment_name,
        max_tasks=args.max_tasks,
        mode=args.mode,
        dataset_path=args.dataset,
    )
    return result, write_experiment_results(result, output_dir=args.out)


def main() -> None:
    args = _parse_args()
    _print_mode_notice()

    print(
        f"\n[RUN] Starting evaluation: experiment={args.experiment_name!r}, "
        f"max_tasks={args.max_tasks!r}\n"
    )

    result, output_paths = asyncio.run(_run(args))

    print("\n" + "=" * 62)
    print("  EVALUATION SUMMARY")
    print("=" * 62)
    def _pct(v):
        return f"{v:.1%}" if v is not None else "n/a"

    print(f"  Total tasks        : {result.total_tasks}")
    print(f"  Eval mode          : {result.eval_mode}")
    print(f"  Average score      : {result.average_score:.4f}")
    print(f"  Average latency (s): {result.average_latency_seconds:.2f}")
    print(f"  Research mode      : {result.research_mode}")
    print(f"  Model provider     : {result.model_provider}")
    print(f"  LangSmith tracing  : {'on' if result.langsmith_tracing else 'off'}")
    if result.langsmith_project:
        print(f"  LangSmith project  : {result.langsmith_project}")
    print(f"  Two-sidedness      : {_pct(result.avg_comparison_two_sidedness)}")
    print(f"  Cmp citation valid : {_pct(result.avg_comparison_citation_validity)}")
    print(f"  Grounding rate     : {_pct(result.avg_grounding_rate)}")
    print(f"  Hallucination rate : {_pct(result.avg_hallucination_rate)}")
    print("\n  Output files:")
    print(f"    JSON     : {output_paths['json']}")
    print(f"    CSV      : {output_paths['csv']}")
    print(f"    Markdown : {output_paths['markdown']}")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
