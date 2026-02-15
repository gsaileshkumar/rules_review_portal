from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.physical_rule import PhysicalRule
from app.models.request import Request
from app.models.semantic_deficiency import SemanticDeficiency
from app.schemas.semantic_search import (
    SemanticMatchedPair,
    SemanticReviewResult,
    SemanticReviewSummary,
    SemanticUnmatchedRequest,
    SemanticUnmatchedRule,
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def run_semantic_review(db: Session, threshold: float | None = None) -> SemanticReviewResult:
    if threshold is None:
        threshold = settings.SIMILARITY_THRESHOLD

    # Clear previous semantic deficiencies
    db.query(SemanticDeficiency).delete()
    db.flush()

    physical_rules = (
        db.query(PhysicalRule)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .all()
    )
    user_requests = db.query(Request).all()

    # Build maps of id -> details and id -> embedding for fast lookup
    rule_details: dict[int, dict] = {}
    rule_embeddings: dict[int, list[float]] = {}
    for rule in physical_rules:
        sources = [s.address for s in rule.sources]
        destinations = [d.address for d in rule.destinations]
        rule_details[rule.rule_id] = {
            "rule_name": rule.rule_name,
            "sources": sources,
            "destinations": destinations,
            "ports": rule.ports,
        }
        if rule.embedding is not None:
            rule_embeddings[rule.rule_id] = [float(x) for x in rule.embedding]

    request_details: dict[int, dict] = {}
    request_embeddings: dict[int, list[float]] = {}
    for req in user_requests:
        data = req.request_json
        request_details[req.request_id] = {
            "name": req.name,
            "sources": data["sources"],
            "destinations": data["destinations"],
            "ports": data["ports"],
        }
        if req.embedding is not None:
            request_embeddings[req.request_id] = [float(x) for x in req.embedding]

    matched: list[SemanticMatchedPair] = []
    unmatched_rules: list[SemanticUnmatchedRule] = []
    matched_request_ids: set[int] = set()

    # For each physical rule, find the best matching request
    for rule_id, rule_emb in rule_embeddings.items():
        best_req_id = None
        best_score = -1.0

        for req_id, req_emb in request_embeddings.items():
            score = _cosine_similarity(rule_emb, req_emb)
            if score > best_score:
                best_score = score
                best_req_id = req_id

        rule_info = rule_details[rule_id]

        if best_req_id is not None and best_score >= threshold:
            req_info = request_details[best_req_id]
            matched.append(
                SemanticMatchedPair(
                    rule_id=rule_id,
                    request_id=best_req_id,
                    rule_name=rule_info["rule_name"],
                    request_name=req_info["name"],
                    sources=rule_info["sources"],
                    destinations=rule_info["destinations"],
                    ports=rule_info["ports"],
                    similarity_score=round(best_score, 4),
                )
            )
            matched_request_ids.add(best_req_id)
        else:
            deficiency = SemanticDeficiency(
                type="no_matching_request",
                rule_id=rule_id,
                best_match_request_id=best_req_id,
                similarity_score=round(best_score, 4) if best_req_id is not None else None,
                threshold_used=threshold,
            )
            db.add(deficiency)
            db.flush()
            unmatched_rules.append(
                SemanticUnmatchedRule(
                    semantic_deficiency_id=deficiency.id,
                    rule_id=rule_id,
                    rule_name=rule_info["rule_name"],
                    sources=rule_info["sources"],
                    destinations=rule_info["destinations"],
                    ports=rule_info["ports"],
                    best_match_request_id=best_req_id,
                    best_match_request_name=request_details[best_req_id]["name"] if best_req_id else None,
                    similarity_score=round(best_score, 4) if best_req_id is not None else None,
                )
            )

    # For rules without embeddings, treat as unmatched
    for rule_id in rule_details:
        if rule_id not in rule_embeddings:
            rule_info = rule_details[rule_id]
            deficiency = SemanticDeficiency(
                type="no_matching_request",
                rule_id=rule_id,
                threshold_used=threshold,
            )
            db.add(deficiency)
            db.flush()
            unmatched_rules.append(
                SemanticUnmatchedRule(
                    semantic_deficiency_id=deficiency.id,
                    rule_id=rule_id,
                    rule_name=rule_info["rule_name"],
                    sources=rule_info["sources"],
                    destinations=rule_info["destinations"],
                    ports=rule_info["ports"],
                    reason="Rule has no embedding — generate embeddings first",
                )
            )

    unmatched_requests: list[SemanticUnmatchedRequest] = []
    for req_id in request_details:
        if req_id not in matched_request_ids:
            req_info = request_details[req_id]
            req_emb = request_embeddings.get(req_id)

            best_rule_id = None
            best_score = -1.0
            if req_emb:
                for rule_id, rule_emb in rule_embeddings.items():
                    score = _cosine_similarity(req_emb, rule_emb)
                    if score > best_score:
                        best_score = score
                        best_rule_id = rule_id

            deficiency = SemanticDeficiency(
                type="no_matching_rule",
                request_id=req_id,
                best_match_rule_id=best_rule_id,
                similarity_score=round(best_score, 4) if best_rule_id is not None else None,
                threshold_used=threshold,
            )
            db.add(deficiency)
            db.flush()
            unmatched_requests.append(
                SemanticUnmatchedRequest(
                    semantic_deficiency_id=deficiency.id,
                    request_id=req_id,
                    request_name=req_info["name"],
                    sources=req_info["sources"],
                    destinations=req_info["destinations"],
                    ports=req_info["ports"],
                    best_match_rule_id=best_rule_id,
                    best_match_rule_name=rule_details[best_rule_id]["rule_name"] if best_rule_id else None,
                    similarity_score=round(best_score, 4) if best_rule_id is not None else None,
                )
            )

    db.commit()

    return SemanticReviewResult(
        matched=matched,
        unmatched_physical_rules=unmatched_rules,
        unmatched_requests=unmatched_requests,
        summary=SemanticReviewSummary(
            total_physical_rules=len(physical_rules),
            total_requests=len(user_requests),
            matched_count=len(matched),
            unmatched_rules_count=len(unmatched_rules),
            unmatched_requests_count=len(unmatched_requests),
            threshold_used=threshold,
        ),
    )
