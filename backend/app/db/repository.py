"""Data-access functions over the SQLite tables. All functions are synchronous;
call them from async code via ``asyncio.to_thread`` (or a route dependency)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.db.database import get_conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Research runs
# ---------------------------------------------------------------------------

def save_run(
    *,
    run_id: str,
    our_company: str,
    competitor: str,
    market: str,
    report_type: str,
    status: str,
    research_mode: str | None,
    confidence_score: float | None,
    source_count: int,
    evidence_count: int,
    verified_claim_count: int,
    warning_count: int,
    duration_ms: float | None,
    report_json: dict[str, Any] | None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO research_runs (
                run_id, our_company, competitor, market, report_type, status,
                research_mode, confidence_score, source_count, evidence_count,
                verified_claim_count, warning_count, duration_ms, created_at, report_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id, our_company, competitor, market, report_type, status,
                research_mode, confidence_score, source_count, evidence_count,
                verified_claim_count, warning_count, duration_ms, _now(),
                json.dumps(report_json) if report_json is not None else None,
            ),
        )


def _run_summary_row(row: Any) -> dict[str, Any]:
    return {
        "runId": row["run_id"],
        "ourCompany": row["our_company"],
        "competitor": row["competitor"],
        "market": row["market"],
        "reportType": row["report_type"],
        "status": row["status"],
        "researchMode": row["research_mode"],
        "confidenceScore": row["confidence_score"],
        "sourceCount": row["source_count"],
        "evidenceCount": row["evidence_count"],
        "verifiedClaimCount": row["verified_claim_count"],
        "warningCount": row["warning_count"],
        "durationMs": row["duration_ms"],
        "createdAt": row["created_at"],
    }


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM research_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_run_summary_row(row) for row in rows]


def get_run(run_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM research_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    if row is None:
        return None
    summary = _run_summary_row(row)
    summary["report"] = json.loads(row["report_json"]) if row["report_json"] else None
    summary["traces"] = get_traces(run_id)
    return summary


def delete_run(run_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM run_traces WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM research_runs WHERE run_id = ?", (run_id,))


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------

def save_traces(run_id: str, traces: list[dict[str, Any]]) -> None:
    if not traces:
        return
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO run_traces (
                run_id, seq, ts, kind, name, status, summary, track, duration_ms, detail_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    run_id,
                    t.get("seq", i),
                    t.get("ts"),
                    t.get("kind", "tool"),
                    t.get("name", ""),
                    t.get("status", "completed"),
                    t.get("summary", ""),
                    t.get("track"),
                    t.get("durationMs"),
                    json.dumps(t.get("detail") or {}),
                )
                for i, t in enumerate(traces)
            ],
        )


def get_traces(run_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM run_traces WHERE run_id = ? ORDER BY seq ASC", (run_id,)
        ).fetchall()
    return [
        {
            "seq": row["seq"],
            "ts": row["ts"],
            "kind": row["kind"],
            "name": row["name"],
            "status": row["status"],
            "summary": row["summary"],
            "track": row["track"],
            "durationMs": row["duration_ms"],
            "detail": json.loads(row["detail_json"]) if row["detail_json"] else {},
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------

def save_evaluation(result: dict[str, Any]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO evaluations (
                experiment_name, created_at, model_provider, research_mode, eval_mode,
                judge_model, total_tasks, average_score, average_latency_seconds,
                average_source_count, result_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                result.get("experiment_name"),
                _now(),
                result.get("model_provider"),
                result.get("research_mode"),
                result.get("eval_mode"),
                result.get("judge_model"),
                result.get("total_tasks"),
                result.get("average_score"),
                result.get("average_latency_seconds"),
                result.get("average_source_count"),
                json.dumps(result),
            ),
        )
        return int(cur.lastrowid or 0)


def list_evaluations(limit: int = 25) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM evaluations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {
            "id": row["id"],
            "experimentName": row["experiment_name"],
            "createdAt": row["created_at"],
            "modelProvider": row["model_provider"],
            "researchMode": row["research_mode"],
            "evalMode": row["eval_mode"],
            "judgeModel": row["judge_model"],
            "totalTasks": row["total_tasks"],
            "averageScore": row["average_score"],
            "averageLatencySeconds": row["average_latency_seconds"],
            "averageSourceCount": row["average_source_count"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
        }
        for row in rows
    ]
