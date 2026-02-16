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

    # Build detail dicts for response construction; no longer loading embeddings into Python.
    rule_details: dict[int, dict] = {}
    for rule in physical_rules:
        sources = [s.address for s in rule.sources]
        destinations = [d.address for d in rule.destinations]
        rule_details[rule.rule_id] = {
            "rule_name": rule.rule_name,
            "sources": sources,
            "destinations": destinations,
            "ports": rule.ports,
        }

    request_details: dict[int, dict] = {}
    for req in user_requests:
        data = req.request_json
        request_details[req.request_id] = {
            "name": req.name,
            "sources": data["sources"],
            "destinations": data["destinations"],
            "ports": data["ports"],
        }

    matched: list[SemanticMatchedPair] = []
    unmatched_rules: list[SemanticUnmatchedRule] = []
    matched_request_ids: set[int] = set()

    # For each physical rule, find the best matching request via pgvector KNN (HNSW index).
    for rule in physical_rules:
        rule_info = rule_details[rule.rule_id]

        if rule.embedding is None:
            deficiency = SemanticDeficiency(
                type="no_matching_request",
                rule_id=rule.rule_id,
                threshold_used=threshold,
            )
            db.add(deficiency)
            db.flush()
            unmatched_rules.append(
                SemanticUnmatchedRule(
                    semantic_deficiency_id=deficiency.id,
                    rule_id=rule.rule_id,
                    rule_name=rule_info["rule_name"],
                    sources=rule_info["sources"],
                    destinations=rule_info["destinations"],
                    ports=rule_info["ports"],
                    reason="Rule has no embedding — generate embeddings first",
                )
            )
            continue

        # KNN query: LIMIT 1 finds the single nearest request using the HNSW index.
        distance_expr = Request.embedding.cosine_distance(list(rule.embedding)).label("distance")
        best_row = (
            db.query(Request, distance_expr)
            .filter(Request.embedding.isnot(None))
            .order_by(distance_expr)
            .first()
        )

        if best_row is not None:
            best_req, best_distance = best_row
            best_score = round(1.0 - best_distance, 4)
            best_req_id = best_req.request_id
        else:
            best_req, best_score, best_req_id = None, -1.0, None

        if best_req is not None and best_score >= threshold:
            matched.append(
                SemanticMatchedPair(
                    rule_id=rule.rule_id,
                    request_id=best_req_id,
                    rule_name=rule_info["rule_name"],
                    request_name=best_req.name,
                    sources=rule_info["sources"],
                    destinations=rule_info["destinations"],
                    ports=rule_info["ports"],
                    similarity_score=best_score,
                )
            )
            matched_request_ids.add(best_req_id)
        else:
            deficiency = SemanticDeficiency(
                type="no_matching_request",
                rule_id=rule.rule_id,
                best_match_request_id=best_req_id,
                similarity_score=best_score if best_req_id is not None else None,
                threshold_used=threshold,
            )
            db.add(deficiency)
            db.flush()
            unmatched_rules.append(
                SemanticUnmatchedRule(
                    semantic_deficiency_id=deficiency.id,
                    rule_id=rule.rule_id,
                    rule_name=rule_info["rule_name"],
                    sources=rule_info["sources"],
                    destinations=rule_info["destinations"],
                    ports=rule_info["ports"],
                    best_match_request_id=best_req_id,
                    best_match_request_name=best_req.name if best_req else None,
                    similarity_score=best_score if best_req_id is not None else None,
                )
            )

    unmatched_requests: list[SemanticUnmatchedRequest] = []
    request_lookup: dict[int, Request] = {r.request_id: r for r in user_requests}

    for req_id in request_details:
        if req_id in matched_request_ids:
            continue

        req = request_lookup[req_id]
        req_info = request_details[req_id]

        best_rule_id = None
        best_rule_name = None
        best_score = None

        if req.embedding is not None:
            # KNN query: LIMIT 1 finds the single nearest rule using the HNSW index.
            distance_expr = PhysicalRule.embedding.cosine_distance(list(req.embedding)).label("distance")
            best_rule_row = (
                db.query(PhysicalRule, distance_expr)
                .filter(PhysicalRule.embedding.isnot(None))
                .order_by(distance_expr)
                .first()
            )
            if best_rule_row is not None:
                best_rule, best_distance = best_rule_row
                best_rule_id = best_rule.rule_id
                best_rule_name = best_rule.rule_name
                best_score = round(1.0 - best_distance, 4)

        deficiency = SemanticDeficiency(
            type="no_matching_rule",
            request_id=req_id,
            best_match_rule_id=best_rule_id,
            similarity_score=best_score,
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
                best_match_rule_name=best_rule_name,
                similarity_score=best_score,
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
