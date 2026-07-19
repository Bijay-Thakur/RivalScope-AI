"""Ported from evals/test_judge.py -> unified evaluation. Judge fully mocked."""

from app.core.config import settings
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
    async def _fake_invoke(messages, model):
        return _FakeVerdict("supported", "matches source", 0.95)

    monkeypatch.setattr(judge, "_invoke_judge", _fake_invoke)
    monkeypatch.setattr(settings, "judge_use_groq", False)
    monkeypatch.setattr(settings, "groq_api_key", None)

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


async def test_judge_claim_records_error_on_failure(monkeypatch):
    async def _raise(messages, model):
        raise RuntimeError("boom")

    monkeypatch.setattr(judge, "_invoke_judge", _raise)
    monkeypatch.setattr(settings, "judge_use_groq", False)
    monkeypatch.setattr(settings, "groq_api_key", None)

    verdict, rationale, confidence = await judge.judge_claim(
        claim="c", source_title="t", source_url="u", source_text="s", model="m"
    )

    assert verdict == Verdict.ERROR
    assert "RuntimeError" in rationale
    assert confidence == 0.0


async def test_judge_claim_falls_back_to_secondary_model(monkeypatch):
    calls: list[str] = []

    async def _invoke(messages, model):
        calls.append(model)
        if model == "gemini-2.5-pro":
            raise RuntimeError("quota exceeded")
        return _FakeVerdict("supported", "ok", 0.9)

    monkeypatch.setattr(judge, "_invoke_judge", _invoke)
    monkeypatch.setattr(settings, "judge_model", "gemini-2.5-pro")
    monkeypatch.setattr(settings, "gemini_model", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "judge_use_groq", False)
    monkeypatch.setattr(settings, "groq_api_key", None)

    verdict, _, confidence = await judge.judge_claim(
        claim="c", source_title="t", source_url="u", source_text="s", model="gemini-2.5-pro"
    )

    assert verdict == Verdict.SUPPORTED
    assert calls == ["gemini-2.5-pro", "gemini-2.5-flash"]
    assert confidence == 0.9


async def test_judge_claims_bounded_concurrency(monkeypatch):
    async def _fake_invoke(messages, model):
        return _FakeVerdict("contradicted", "opposite", 0.8)

    monkeypatch.setattr(judge, "_invoke_judge", _fake_invoke)
    monkeypatch.setattr(settings, "judge_use_groq", False)
    monkeypatch.setattr(settings, "groq_api_key", None)

    items = [
        {"claim": f"c{i}", "source_title": "t", "source_url": "u", "source_text": "s"}
        for i in range(5)
    ]
    results = await judge.judge_claims(items, model="gemini-2.5-pro", max_concurrency=2)

    assert len(results) == 5
    assert all(v == Verdict.CONTRADICTED for v, _, _ in results)


async def test_judge_claims_empty_list_short_circuits():
    assert await judge.judge_claims([], model="m") == []


def test_judge_use_groq_puts_groq_first_with_gemini_fallback(monkeypatch):
    monkeypatch.setattr(settings, "judge_use_groq", True)
    monkeypatch.setattr(settings, "groq_api_key", "g")
    monkeypatch.setattr(settings, "groq_model", "llama-3.1-8b-instant")
    monkeypatch.setattr(settings, "judge_model", "gemini-2.5-flash-lite")
    monkeypatch.setattr(settings, "gemini_model", "gemini-2.5-flash")
    assert judge.judge_model_candidates() == [
        "groq:llama-3.1-8b-instant",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]


async def test_judge_error_path_null_grounding_rate(monkeypatch):
    """ERROR verdicts must not collapse into grounding_rate=0.0."""
    from app.evaluation.scorers import grounding_metrics
    from app.evaluation.schemas import ClaimVerdict

    async def _raise(messages, model):
        raise RuntimeError("quota")

    monkeypatch.setattr(judge, "_invoke_judge", _raise)
    monkeypatch.setattr(settings, "judge_use_groq", False)
    monkeypatch.setattr(settings, "groq_api_key", None)

    verdict, rationale, conf = await judge.judge_claim(
        claim="c", source_title="t", source_url="u", source_text="s", model="m"
    )
    assert verdict == Verdict.ERROR

    gm = grounding_metrics(
        [
            ClaimVerdict(
                claim="c",
                source_id="s",
                self_confidence="high",
                verdict=verdict,
                rationale=rationale,
                judge_confidence=conf,
            )
        ]
    )
    assert gm["n_judge_errors"] == 1
    assert gm["n_judged_ok"] == 0
    assert gm["grounding_rate"] is None
    assert gm["hallucination_rate"] is None


async def test_judge_success_mixed_verdicts_math(monkeypatch):
    from app.evaluation.scorers import grounding_metrics
    from app.evaluation.schemas import ClaimVerdict

    seq = iter(
        [
            _FakeVerdict("supported", "ok", 0.9),
            _FakeVerdict("unsupported", "silent", 0.8),
            _FakeVerdict("contradicted", "opp", 0.7),
            _FakeVerdict("partial", "part", 0.6),
        ]
    )

    async def _fake(messages, model):
        return next(seq)

    monkeypatch.setattr(judge, "_invoke_judge", _fake)
    monkeypatch.setattr(settings, "judge_use_groq", False)
    monkeypatch.setattr(settings, "groq_api_key", None)
    items = [
        {"claim": f"c{i}", "source_title": "t", "source_url": "u", "source_text": "s"}
        for i in range(4)
    ]
    results = await judge.judge_claims(items, model="m", max_concurrency=1)
    verdicts = [
        ClaimVerdict(
            claim=f"c{i}",
            source_id="s",
            self_confidence="high",
            verdict=v,
            rationale=r,
            judge_confidence=c,
        )
        for i, (v, r, c) in enumerate(results)
    ]
    gm = grounding_metrics(verdicts)
    assert gm["n_judged_ok"] == 4
    assert gm["n_judge_errors"] == 0
    assert gm["grounding_rate"] == 2 / 4  # supported + partial
    assert gm["hallucination_rate"] == 1 / 4
