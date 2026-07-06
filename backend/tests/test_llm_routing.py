"""Part A — payload-aware LLM routing + context budget. All externals mocked."""

import app.services.llm as llm
from app.core.config import settings
from app.schemas.report import EvidenceItem, Source
from app.services.context_budget import trim_evidence_to_budget


class _FakeLLM:
    def __init__(self, tag):
        self.tag = tag

    def invoke(self, messages):
        return f"OK:{self.tag}"


def _msgs(chars: int):
    return [{"role": "user", "content": "x" * chars}]


def test_big_payload_skips_groq(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_max_payload_chars", 100)
    monkeypatch.setattr(settings, "google_api_key", "fake")
    monkeypatch.setattr(settings, "gemini_api_key", None)

    called = {"primary": False}

    def _primary(temp=0.1):
        called["primary"] = True
        return _FakeLLM("groq")

    monkeypatch.setattr(llm, "get_primary_llm", _primary)
    monkeypatch.setattr(llm, "get_fallback_llm", lambda temp=0.1: _FakeLLM("gemini"))

    result = llm.invoke_with_fallback(_msgs(500))
    assert result == "OK:gemini"
    assert called["primary"] is False  # Groq never touched -> no wasted 413


def test_small_payload_uses_groq_first(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_max_payload_chars", 10000)
    monkeypatch.setattr(settings, "google_api_key", "fake")

    monkeypatch.setattr(llm, "get_primary_llm", lambda temp=0.1: _FakeLLM("groq"))
    monkeypatch.setattr(llm, "get_fallback_llm", lambda temp=0.1: _FakeLLM("gemini"))

    result = llm.invoke_with_fallback(_msgs(50))
    assert result == "OK:groq"


def _src(id_, cred):
    return Source(id=id_, title=id_, url=f"https://x/{id_}", source_type="other", credibility_score=cred)


def _ev(id_, source_id, company, chars):
    return EvidenceItem(id=id_, claim="c", source_id=source_id, confidence="low",
                        company=company, raw_text="y" * chars)


def test_budget_trim_drops_lowest_cred_keeps_both_sides():
    sources = [
        _src("s1", 0.9), _src("s2", 0.1), _src("s3", 0.2), _src("s4", 0.95),
    ]
    evidence = [
        _ev("a", "s1", "Our", 400),
        _ev("b", "s2", "Our", 400),   # lowest cred our -> first to go
        _ev("c", "s3", "Rival", 400), # low cred rival
        _ev("d", "s4", "Rival", 400),
    ]
    # budget forces dropping ~2 items (1600 total -> cap 900)
    kept = trim_evidence_to_budget(evidence, sources, "Our", "Rival", 900)

    ids = {e.id for e in kept}
    assert "b" not in ids  # lowest-cred our dropped
    # both sides still represented
    assert any(e.company == "Our" for e in kept)
    assert any(e.company == "Rival" for e in kept)


def test_budget_never_zeroes_a_side():
    sources = [_src("s1", 0.1), _src("s2", 0.1)]
    evidence = [_ev("a", "s1", "Our", 5000), _ev("b", "s2", "Rival", 5000)]
    # cap way under, but each side has exactly one -> cannot drop either
    kept = trim_evidence_to_budget(evidence, sources, "Our", "Rival", 100)
    assert any(e.company == "Our" for e in kept)
    assert any(e.company == "Rival" for e in kept)


def test_budget_noop_when_under():
    sources = [_src("s1", 0.5)]
    evidence = [_ev("a", "s1", "Our", 10)]
    kept = trim_evidence_to_budget(evidence, sources, "Our", "Rival", 10000)
    assert kept == evidence
