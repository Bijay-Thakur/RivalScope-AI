import json

from app.core.logging import write_run_log
from app.graph.workflow import run_research_graph
from app.schemas.research import ReportType, ResearchRequest


def test_write_run_log_appends_json_line(tmp_path, monkeypatch):
    log_file = tmp_path / "research_runs.jsonl"
    monkeypatch.setattr("app.core.logging.LOG_DIR", tmp_path)
    monkeypatch.setattr("app.core.logging.RUN_LOG_FILE", log_file)

    write_run_log("run-123", "run_started", {"request": {"competitor": "Notion"}})

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["run_id"] == "run-123"
    assert record["event_type"] == "run_started"
    assert record["payload"]["request"]["competitor"] == "Notion"
    assert "timestamp" in record


def test_run_research_graph_writes_lifecycle_logs(tmp_path, monkeypatch):
    log_file = tmp_path / "research_runs.jsonl"
    monkeypatch.setattr("app.core.logging.LOG_DIR", tmp_path)
    monkeypatch.setattr("app.core.logging.RUN_LOG_FILE", log_file)

    run_research_graph(
        ResearchRequest(
            our_company="ClickUp",
            competitor="Notion",
            market="Project management / docs",
            report_type=ReportType.QUICK_BRIEF,
        )
    )

    records = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines() if line]
    event_types = [record["event_type"] for record in records]
    assert event_types == ["run_started", "graph_completed"]
