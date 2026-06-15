from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.report import CompetitorReport


class ReportType(StrEnum):
    QUICK_BRIEF = "quick_brief"
    DEEP_RESEARCH = "deep_research"
    SALES_BATTLECARD = "sales_battlecard"


class ResearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    our_company: str = Field(alias="ourCompany")
    competitor: str
    market: str
    report_type: ReportType = Field(alias="reportType")


class ResearchTask(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: str
    track: str
    objective: str
    priority: int


class ResearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    report: CompetitorReport
