from app.evaluation.loader import load_benchmark_tasks
from app.evaluation.schemas import BenchmarkTask


def test_benchmark_loads_successfully():
    tasks = load_benchmark_tasks()

    assert isinstance(tasks, list)
    assert tasks


def test_benchmark_contains_at_least_20_tasks():
    tasks = load_benchmark_tasks()

    assert len(tasks) >= 20


def test_each_task_validates_as_benchmark_task():
    tasks = load_benchmark_tasks()

    for task in tasks:
        assert isinstance(task, BenchmarkTask)
        assert task.id
        assert task.our_company
        assert task.competitor
        assert task.market
        assert task.report_type
        assert task.expected_sections
        assert task.expected_source_types
        assert task.expected_facts
