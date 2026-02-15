from pydantic import BaseModel


class MatchedPair(BaseModel):
    rule_id: int
    request_id: int
    sources: list[str]
    destinations: list[str]
    ports: list[str]


class UnmatchedRule(BaseModel):
    deficiency_id: int
    rule_id: int
    rule_name: str
    sources: list[str]
    destinations: list[str]
    ports: list[str]
    reason: str = "No matching user request found"


class UnmatchedRequest(BaseModel):
    deficiency_id: int
    request_id: int
    name: str
    sources: list[str]
    destinations: list[str]
    ports: list[str]
    reason: str = "No matching physical rule found"


class ReviewSummary(BaseModel):
    total_physical_rules: int
    total_requests: int
    matched_count: int
    unmatched_rules_count: int
    unmatched_requests_count: int


class ReviewResult(BaseModel):
    matched: list[MatchedPair]
    unmatched_physical_rules: list[UnmatchedRule]
    unmatched_requests: list[UnmatchedRequest]
    summary: ReviewSummary
