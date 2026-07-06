import pytest

from app.core.config import settings
from app.evaluation.runner import run_evaluation
from app.evaluation.schemas import ExperimentResult, TaskScore


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "research_mode", "mock")


@pytest.fixture(autouse=True)
def clear_api_keys(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "google_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "tavily_api_key", None)


async def test_run_evaluation_works_in_mock_mode_with_max_tasks():
    result = await run_evaluation(
        experiment_name="phase4_test_mock",
        max_tasks=1,
    )

    assert isinstance(result, ExperimentResult)
    assert result.experiment_name == "phase4_test_mock"
    assert result.research_mode == "mock"
    assert result.total_tasks == 1
    assert len(result.task_scores) == 1

    task_score = result.task_scores[0]
    assert isinstance(task_score, TaskScore)
    assert task_score.task_id
    assert task_score.overall_score > 0.0
    assert task_score.source_count > 0
    assert result.average_score == task_score.overall_score
    assert result.average_latency_seconds >= 0.0
    assert result.average_source_count == float(task_score.source_count)
