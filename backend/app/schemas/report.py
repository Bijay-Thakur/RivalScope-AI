from pydantic import BaseModel, ConfigDict, Field


class Source(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: str
    title: str
    url: str
    source_type: str = Field(alias="sourceType")
    published_date: str | None = Field(default=None, alias="publishedDate")
    credibility_score: float = Field(alias="credibilityScore")
    retrieved_at: str | None = None
    snippet: str | None = None
    company: str | None = None


class EvidenceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: str
    claim: str
    source_id: str = Field(alias="sourceId")
    confidence: str
    evidence_type: str | None = None
    url: str | None = None
    raw_text: str | None = None
    company: str | None = None


class FeatureComparisonRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    dimension: str
    our_value: str = Field(alias="ourValue")
    competitor_value: str = Field(alias="competitorValue")
    our_source_ids: list[str] = Field(default_factory=list, alias="ourSourceIds")
    competitor_source_ids: list[str] = Field(default_factory=list, alias="competitorSourceIds")
    advantage: str  # our | competitor | parity | unclear


class ComparisonMatrix(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    rows: list[FeatureComparisonRow]
    pricing_comparison: str = Field(alias="pricingComparison")
    positioning_gap: str = Field(alias="positioningGap")
    summary: str


class VerifiedClaim(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    id: str
    claim: str
    source_ids: list[str] = Field(alias="sourceIds")
    verification_status: str = Field(alias="verificationStatus")
    confidence_score: float = Field(alias="confidenceScore")


class SalesBattlecard(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    talk_tracks: list[str] = Field(alias="talkTracks")
    objection_handling: list[str] = Field(alias="objectionHandling")
    landmines: list[str]


class CompetitorReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    company_snapshot: str = Field(alias="companySnapshot")
    product_positioning: str = Field(alias="productPositioning")
    feature_comparison: list[str] = Field(alias="featureComparison")
    pricing_intelligence: str = Field(alias="pricingIntelligence")
    recent_moves: list[str] = Field(alias="recentMoves")
    strengths: list[str]
    weaknesses: list[str]
    sales_battlecard: SalesBattlecard = Field(alias="salesBattlecard")
    comparison_matrix: "ComparisonMatrix | None" = Field(default=None, alias="comparisonMatrix")
    evidence: list[EvidenceItem]
    sources: list[Source]
    confidence_score: float = Field(alias="confidenceScore", ge=0, le=100)
    generated_at: str | None = None
    research_mode: str | None = None
    warnings: list[str] = []
