from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProgressStatus = Literal["pending", "running", "completed", "failed"]
StreamEventType = Literal["progress", "final_report", "error"]


class ProgressEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    run_id: str = Field(alias="runId")
    step: int
    name: str
    message: str
    status: ProgressStatus


class ResearchStreamEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    event_type: StreamEventType = Field(alias="eventType")
    data: dict[str, object]
