from typing import Optional

from pydantic import BaseModel, computed_field


class SemanticMatch(BaseModel):
    rule_id: Optional[int] = None
    request_id: Optional[int] = None
    name: str
    sources: list[str]
    destinations: list[str]
    ports: list[str]
    similarity_score: float

    @computed_field
    @property
    def similarity_percent(self) -> int:
        return round(self.similarity_score * 100)


class SemanticSearchResult(BaseModel):
    query_id: int
    query_type: str  # "request" or "rule"
    query_text: str
    matches: list[SemanticMatch]
    total_matches: int
    threshold_used: float


class TextSearchRequest(BaseModel):
    query: str
    search_in: str = "both"  # "rules", "requests", "both"
    threshold: float = 0.7
    limit: int = 10


class TextSearchMatch(BaseModel):
    entity_type: str  # "rule" or "request"
    rule_id: Optional[int] = None
    request_id: Optional[int] = None
    name: str
    sources: list[str]
    destinations: list[str]
    ports: list[str]
    similarity_score: float

    @computed_field
    @property
    def similarity_percent(self) -> int:
        return round(self.similarity_score * 100)


class TextSearchResult(BaseModel):
    query: str
    matches: list[TextSearchMatch]
    total_matches: int
    threshold_used: float


class EmbeddingStatus(BaseModel):
    total_requests: int
    requests_with_embeddings: int
    total_rules: int
    rules_with_embeddings: int


class EmbeddingGenerateResult(BaseModel):
    requests_generated: int
    rules_generated: int
    requests_skipped: int
    rules_skipped: int


class SemanticMatchedPair(BaseModel):
    rule_id: int
    request_id: int
    rule_name: str
    request_name: str
    sources: list[str]
    destinations: list[str]
    ports: list[str]
    similarity_score: float

    @computed_field
    @property
    def similarity_percent(self) -> int:
        return round(self.similarity_score * 100)


class SemanticUnmatchedRule(BaseModel):
    semantic_deficiency_id: int
    rule_id: int
    rule_name: str
    sources: list[str]
    destinations: list[str]
    ports: list[str]
    best_match_request_id: Optional[int] = None
    best_match_request_name: Optional[str] = None
    similarity_score: Optional[float] = None
    reason: str = "No semantically similar user request found above threshold"


class SemanticUnmatchedRequest(BaseModel):
    semantic_deficiency_id: int
    request_id: int
    request_name: str
    sources: list[str]
    destinations: list[str]
    ports: list[str]
    best_match_rule_id: Optional[int] = None
    best_match_rule_name: Optional[str] = None
    similarity_score: Optional[float] = None
    reason: str = "No semantically similar physical rule found above threshold"


class SemanticReviewSummary(BaseModel):
    total_physical_rules: int
    total_requests: int
    matched_count: int
    unmatched_rules_count: int
    unmatched_requests_count: int
    threshold_used: float


class SemanticReviewResult(BaseModel):
    matched: list[SemanticMatchedPair]
    unmatched_physical_rules: list[SemanticUnmatchedRule]
    unmatched_requests: list[SemanticUnmatchedRequest]
    summary: SemanticReviewSummary


class SemanticDeficiencyResponse(BaseModel):
    id: int
    type: str
    request_id: Optional[int] = None
    rule_id: Optional[int] = None
    best_match_request_id: Optional[int] = None
    best_match_rule_id: Optional[int] = None
    similarity_score: Optional[float] = None
    threshold_used: float

    class Config:
        from_attributes = True
