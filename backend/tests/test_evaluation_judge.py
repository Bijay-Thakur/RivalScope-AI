"""Ported from evals/test_judge.py -> unified evaluation. Judge fully mocked."""

from app.evaluation import judge
from app.evaluation.schemas import Verdict


class _FakeVerdict:
    def __init__(self, verdict: str, rationale: str, judge_confidence: float):
        self.verdict = verdict
        self.rationale = rationale
        self.judge_confidence = judge_confidence


class _FakeLLM:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, messages):
        return self._result


async def test_judge_claim_parses_supported_verdict(monkeypatch):
    fake = _FakeLLM(_FakeVerdict("supported", "matches source", 0.95))
    monkeypatch.setattr(judge, "_get_judge_llm", lambda model: fake)

    verdict, rationale, confidence = await judge.judge_claim(
        claim="X raised $10M",
        source_title="X press release",
        source_url="https://x.com/news",
        source_text="X announced a $10M funding round.",
        model="gemini-2.5-pro",
    )

    assert verdict == Verdict.SUPPORTED
    assert rationale == "matches source"
    assert confidence == 0.95


async def test_judge_claim_defaults_to_unsupported_on_error(monkeypatch):
    def _raise(model):
        raise RuntimeError("boom")

    monkeypatch.setattr(judge, "_get_judge_llm", _raise)

    verdict, rationale, confidence = await judge.judge_claim(
        claim="c", source_title="t", source_url="u", source_text="s", model="m"
    )

    assert verdict == Verdict.UNSUPPORTED
    assert "boom" in rationale or "RuntimeError" in rationale
    assert confidence == 0.0


async def test_judge_claims_bounded_concurrency(monkeypatch):
    fake = _FakeLLM(_FakeVerdict("contradicted", "opposite", 0.8))
    monkeypatch.setattr(judge, "_get_judge_llm", lambda model: fake)

    items = [
        {"claim": f"c{i}", "source_title": "t", "source_url": "u", "source_text": "s"}
        for i in range(5)
    ]
    results = await judge.judge_claims(items, model="gemini-2.5-pro", max_concurrency=2)

    assert len(results) == 5
    assert all(v == Verdict.CONTRADICTED for v, _, _ in results)


async def test_judge_claims_empty_list_short_circuits():
    assert await judge.judge_claims([], model="m") == []
