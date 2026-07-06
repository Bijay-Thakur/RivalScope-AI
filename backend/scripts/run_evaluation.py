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
        default="phase4_baseline",
        help="Name for this evaluation run (default: phase4_baseline)",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help="Limit the number of benchmark tasks to run",
    )
    return parser.parse_args()


def _print_mode_notice() -> None:
    from app.core.config import settings

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
    )
    return result, write_experiment_results(result)


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
    print(f"  Total tasks        : {result.total_tasks}")
    print(f"  Average score      : {result.average_score:.4f}")
    print(f"  Average latency (s): {result.average_latency_seconds:.2f}")
    print(f"  Research mode      : {result.research_mode}")
    print(f"  Model provider     : {result.model_provider}")
    print("\n  Output files:")
    print(f"    JSON     : {output_paths['json']}")
    print(f"    CSV      : {output_paths['csv']}")
    print(f"    Markdown : {output_paths['markdown']}")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
