"""In-process tool-use trace buffer.

Captures EVERY external call the agent makes — not just LLM calls, but tool
calls too (Tavily web search, Tavily page extraction) — with timing, status,
and human-readable summaries. Traces are keyed by run_id, streamed to the UI
"Streaming Log", and persisted to the run history DB.

This is intentionally lightweight and dependency-free (a thread-safe dict) so it
works whether or not LangSmith is installed/enabled. LangSmith, when turned on,
gives you a hosted trace tree; this buffer gives you first-class, always-on tool
traces inside the app itself.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_runs: dict[str, list[dict[str, Any]]] = {}
_seq: dict[str, int] = {}

# Trace "kind": what category of work produced this span.
KIND_TOOL = "tool"  # external tool call (web search, page extract)
KIND_LLM = "llm"  # language-model call
KIND_NODE = "node"  # graph node boundary (coarse pipeline step)


def start_run(run_id: str) -> None:
    with _lock:
        _runs[run_id] = []
        _seq[run_id] = 0


def _next_seq(run_id: str) -> int:
    _seq[run_id] = _seq.get(run_id, 0) + 1
    return _seq[run_id]


def record(
    run_id: str | None,
    *,
    kind: str,
    name: str,
    status: str = "completed",
    summary: str = "",
    track: str | None = None,
    duration_ms: float | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Append a single trace span for a run. No-op when run_id is None."""
    if not run_id:
        return
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "name": name,
        "status": status,
        "summary": summary,
        "track": track,
        "durationMs": round(duration_ms, 1) if duration_ms is not None else None,
        "detail": detail or {},
    }
    with _lock:
        bucket = _runs.setdefault(run_id, [])
        event["seq"] = _next_seq(run_id)
        bucket.append(event)


@contextmanager
def trace_call(
    run_id: str | None,
    *,
    kind: str,
    name: str,
    track: str | None = None,
    summary: str = "",
    detail: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Time a tool/LLM call and record exactly one span when it finishes.

    Yields a mutable ``holder`` — set ``holder["summary"]`` / ``holder["detail"]``
    inside the block to describe the result (e.g. how many results came back).
    Records status="failed" if the block raises, then re-raises.
    """
    holder: dict[str, Any] = {"summary": summary, "detail": dict(detail or {})}
    started = time.perf_counter()
    status = "completed"
    try:
        yield holder
    except Exception:
        status = "failed"
        raise
    finally:
        record(
            run_id,
            kind=kind,
            name=name,
            status=status,
            summary=holder.get("summary", summary),
            track=track,
            duration_ms=(time.perf_counter() - started) * 1000.0,
            detail=holder.get("detail"),
        )


def get(run_id: str) -> list[dict[str, Any]]:
    with _lock:
        return list(_runs.get(run_id, []))


def pop(run_id: str) -> list[dict[str, Any]]:
    """Return and clear a run's traces (frees memory after streaming/persisting)."""
    with _lock:
        events = _runs.pop(run_id, [])
        _seq.pop(run_id, None)
        return events
