"""Real-time SSE generator: agent_status (working/done) as nodes run, token deltas
best-effort, final_report last, error path. Graph fully mocked — zero real API calls."""

import json

import pytest

import app.api.routes.research as research
from app.core.config import settings
from app.schemas.events import ProgressEvent
from app.schemas.research import ReportType, ResearchRequest
from app.services.mock_data import build_mock_report

_REQUEST = ResearchRequest(
    our_company="ClickUp",
    competitor="Notion",
    market="PM software",
    report_type=ReportType.SALES_BATTLECARD,
)


class _FakeGraph:
    def __init__(self, events):
        self._events = events

    async def astream_events(self, state, version="v2"):
        for ev in self._events:
            yield ev


def _node_start(name):
    return {"event": "on_chain_start", "name": name, "run_id": f"n-{name}", "data": {}, "metadata": {}}


def _node_end(name, message):
    pe = ProgressEvent(run_id="r", step=1, name=name, message=message, status="completed")
    return {
        "event": "on_chain_end",
        "name": name,
        "run_id": f"n-{name}",
        "data": {"output": {"progress_events": [pe]}},
        "metadata": {},
    }


def _token(node, text):
    return {
        "event": "on_chat_model_stream",
        "name": "ChatGoogleGenerativeAI",
        "run_id": "llm-1",
        "data": {"chunk": type("C", (), {"content": text})()},
        "metadata": {"langgraph_node": node},
    }


def _root_start():
    return {"event": "on_chain_start", "name": "LangGraph", "run_id": "root", "data": {}, "metadata": {}}


def _root_end(report):
    return {
        "event": "on_chain_end",
        "name": "LangGraph",
        "run_id": "root",
        "data": {"output": {"final_report": report}},
        "metadata": {},
    }


def _install(monkeypatch, events):
    monkeypatch.setattr(settings, "research_mode", "mock")
    monkeypatch.setattr(research, "build_research_graph", lambda: _FakeGraph(events))
    monkeypatch.setattr(research, "write_run_log", lambda *a, **k: None)
    monkeypatch.setattr(research, "log_graph_completed", lambda *a, **k: None)


async def _collect(monkeypatch, events):
    _install(monkeypatch, events)
    return [chunk async for chunk in research._research_stream_events(_REQUEST)]


def _parse(chunk):
    lines = chunk.strip().split("\n")
    event = lines[0].removeprefix("event: ")
    data = json.loads(lines[1].removeprefix("data: "))
    return event, data


async def test_status_working_then_done_in_order_and_final_report_last(monkeypatch):
    report = build_mock_report(_REQUEST)
    events = [
        _root_start(),
        _node_start("normalize_input"),
        _node_end("normalize_input", "normalized"),
        _node_start("report_generator"),
        _node_end("report_generator", "report written"),
        _root_end(report),
    ]
    chunks = await _collect(monkeypatch, events)
    parsed = [_parse(c) for c in chunks]

    kinds = [(e, d.get("status")) for e, d in parsed]
    assert kinds[0] == ("agent_status", "working")  # normalize_input start
    assert kinds[1] == ("agent_status", "done")
    assert ("agent_status", "working") in kinds  # report_generator working
    assert parsed[-1][0] == "final_report"  # report last

    done_norm = next(d for e, d in parsed if e == "agent_status" and d["name"] == "normalize_input" and d["status"] == "done")
    assert done_norm["message"] == "normalized"


async def test_tokens_streamed_for_llm_node(monkeypatch):
    report = build_mock_report(_REQUEST)
    events = [
        _root_start(),
        _node_start("report_generator"),
        _token("report_generator", "Hello "),
        _token("report_generator", "world"),
        _node_end("report_generator", "done"),
        _root_end(report),
    ]
    parsed = [_parse(c) for c in await _collect(monkeypatch, events)]
    tokens = [d for e, d in parsed if e == "token"]
    assert [t["delta"] for t in tokens] == ["Hello ", "world"]
    assert all(t["node"] == "report_generator" for t in tokens)


async def test_degrade_no_tokens_still_full_status_and_report(monkeypatch):
    """Acceptance #4: absent token events must not break status/final_report."""
    report = build_mock_report(_REQUEST)
    events = [
        _root_start(),
        _node_start("comparison_agent"),
        _node_end("comparison_agent", "compared"),
        _root_end(report),
    ]
    parsed = [_parse(c) for c in await _collect(monkeypatch, events)]
    assert not any(e == "token" for e, _ in parsed)
    assert any(e == "agent_status" and d["status"] == "working" for e, d in parsed)
    assert any(e == "agent_status" and d["status"] == "done" for e, d in parsed)
    assert parsed[-1][0] == "final_report"


async def test_no_report_yields_error(monkeypatch):
    events = [_root_start(), _node_start("normalize_input"), _node_end("normalize_input", "x"), _root_end(None)]
    parsed = [_parse(c) for c in await _collect(monkeypatch, events)]
    assert parsed[-1][0] == "error"


async def test_graph_exception_yields_error(monkeypatch):
    class _Boom:
        async def astream_events(self, state, version="v2"):
            yield _root_start()
            raise RuntimeError("boom")

    monkeypatch.setattr(settings, "research_mode", "mock")
    monkeypatch.setattr(research, "build_research_graph", lambda: _Boom())
    monkeypatch.setattr(research, "write_run_log", lambda *a, **k: None)

    parsed = [_parse(c) for c in [x async for x in research._research_stream_events(_REQUEST)]]
    assert parsed[-1][0] == "error"


async def test_real_mode_missing_keys_yields_error(monkeypatch):
    monkeypatch.setattr(settings, "research_mode", "real")
    monkeypatch.setattr(settings, "tavily_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "google_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)

    parsed = [_parse(c) for c in [x async for x in research._research_stream_events(_REQUEST)]]
    assert parsed[0][0] == "error"
