import json
from pathlib import Path

from pydantic import ValidationError

from app.evaluation.schemas import BenchmarkTask

DEFAULT_BENCHMARK_TASKS_PATH = (
    Path(__file__).resolve().parent / "benchmark_tasks.json"
)


def load_benchmark_tasks(path: str | None = None) -> list[BenchmarkTask]:
    task_path = Path(path) if path is not None else DEFAULT_BENCHMARK_TASKS_PATH

    if not task_path.is_file():
        raise FileNotFoundError(f"Benchmark tasks file not found: {task_path}")

    try:
        raw_data = json.loads(task_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in benchmark tasks file: {task_path}"
        ) from exc

    if not isinstance(raw_data, list):
        raise ValueError(
            f"Benchmark tasks file must contain a JSON array: {task_path}"
        )

    tasks: list[BenchmarkTask] = []
    for index, item in enumerate(raw_data):
        try:
            tasks.append(BenchmarkTask.model_validate(item))
        except ValidationError as exc:
            raise ValueError(
                f"Invalid benchmark task at index {index} in {task_path}: {exc}"
            ) from exc

    return tasks
