from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.report import CompetitorReport
from app.services.compare_features import market_from_features, normalize_compare_features


class ReportType(StrEnum):
    QUICK_BRIEF = "quick_brief"
    DEEP_RESEARCH = "deep_research"
    SALES_BATTLECARD = "sales_battlecard"


class ResearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    our_company: str = Field(alias="ourCompany")
    competitor: str
    # Kept for DB/eval/back-compat. Derived from compare_features when blank.
    market: str = ""
    report_type: ReportType = Field(alias="reportType")
    compare_features: list[str] = Field(default_factory=list, alias="compareFeatures")

    @model_validator(mode="after")
    def _normalize_features_and_market(self) -> Self:
        feats = normalize_compare_features(self.compare_features)
        object.__setattr__(self, "compare_features", feats)
        market = (self.market or "").strip()
        if not market:
            market = market_from_features(feats)
        object.__setattr__(self, "market", market)
        return self


class ResearchTask(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: str
    track: str
    objective: str
    priority: int


class ResearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    report: CompetitorReport
