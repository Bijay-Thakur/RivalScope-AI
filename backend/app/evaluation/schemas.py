from pydantic import BaseModel


class BenchmarkTask(BaseModel):
    id: str
    our_company: str
    competitor: str
    market: str
    report_type: str
    expected_sections: list[str]
    expected_source_types: list[str]
    expected_facts: list[str]
    notes: str | None = None


class TaskScore(BaseModel):
    task_id: str
    task_completion: float
    section_coverage: float
    source_coverage: float
    citation_integrity: float
    evidence_count: int
    source_count: int
    latency_seconds: float
    warnings_count: int
    overall_score: float
    failure_notes: list[str]


class ExperimentResult(BaseModel):
    experiment_name: str
    model_provider: str
    research_mode: str
    total_tasks: int
    average_score: float
    average_latency_seconds: float
    average_source_count: float
    task_scores: list[TaskScore]
