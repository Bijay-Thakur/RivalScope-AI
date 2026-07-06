import pytest

from app.core.config import settings
from app.evaluation import runner
from app.evaluation.runner import run_evaluation
from app.evaluation.schemas import ExperimentResult, TaskScore, Verdict


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


async def test_structural_mode_makes_zero_judge_calls(monkeypatch):
    called = {"n": 0}

    async def _spy(items, model, max_concurrency=3):
        called["n"] += 1
        return [(Verdict.SUPPORTED, "r", 0.9) for _ in items]

    monkeypatch.setattr(runner, "judge_claims", _spy)

    result = await run_evaluation("struct", max_tasks=1, mode="structural")

    assert called["n"] == 0  # no LLM judge in structural mode
    assert result.eval_mode == "structural"
    assert result.judge_model is None
    ts = result.task_scores[0]
    # deterministic comparison metrics still computed from the mock matrix
    assert ts.comparison_two_sidedness is not None
    assert ts.comparison_citation_validity is not None
    # grounding (judge) left unpopulated
    assert ts.grounding_rate is None
    assert result.avg_grounding_rate is None


async def test_full_mode_invokes_judge(monkeypatch):
    called = {"n": 0}

    async def _spy(items, model, max_concurrency=3):
        called["n"] += 1
        return [(Verdict.SUPPORTED, "r", 0.9) for _ in items]

    monkeypatch.setattr(runner, "judge_claims", _spy)

    result = await run_evaluation("full", max_tasks=1, mode="full")

    assert called["n"] > 0  # judge invoked
    assert result.eval_mode == "full"
    assert result.judge_model is not None
    ts = result.task_scores[0]
    assert ts.grounding_rate is not None
    assert ts.hallucination_rate is not None


async def test_limit_respected(monkeypatch):
    async def _spy(items, model, max_concurrency=3):
        return [(Verdict.SUPPORTED, "r", 0.9) for _ in items]

    monkeypatch.setattr(runner, "judge_claims", _spy)

    result = await run_evaluation("lim", max_tasks=2, mode="structural")
    assert result.total_tasks == 2
