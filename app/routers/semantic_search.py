from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.physical_rule import PhysicalRule
from app.models.request import Request
from app.schemas.semantic_search import (
    SemanticMatch,
    SemanticSearchResult,
    TextSearchMatch,
    TextSearchRequest,
    TextSearchResult,
)
from app.services import embedding_service

router = APIRouter(prefix="/api/semantic-search", tags=["semantic-search"])


@router.post("/by-request/{request_id}", response_model=SemanticSearchResult)
def search_by_request(
    request_id: int,
    threshold: float = 0.7,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Find physical rules semantically similar to the given request."""
    req = db.query(Request).filter(Request.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Generate embedding on the fly if missing
    if req.embedding is None:
        data = req.request_json
        text = embedding_service.build_request_text(
            req.name, data["sources"], data["destinations"], data["ports"]
        )
        req.embedding_text = text
        req.embedding = embedding_service.embed(text)
        db.commit()

    query_embedding = list(req.embedding)
    query_text = req.embedding_text or ""

    # KNN query: ORDER BY embedding <=> query_vector activates the HNSW index.
    # Over-fetch by 4x to account for threshold post-filtering.
    distance_expr = PhysicalRule.embedding.cosine_distance(query_embedding).label("distance")
    rows = (
        db.query(PhysicalRule, distance_expr)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .filter(PhysicalRule.embedding.isnot(None))
        .order_by(distance_expr)
        .limit(limit * 4)
        .all()
    )

    # Results are already ordered by similarity descending (distance ascending).
    matches = []
    for rule, distance in rows:
        score = round(1.0 - distance, 4)
        if score >= threshold:
            sources = [s.address for s in rule.sources]
            destinations = [d.address for d in rule.destinations]
            matches.append(
                SemanticMatch(
                    rule_id=rule.rule_id,
                    name=rule.rule_name,
                    sources=sources,
                    destinations=destinations,
                    ports=rule.ports,
                    similarity_score=score,
                )
            )

    matches = matches[:limit]

    return SemanticSearchResult(
        query_id=request_id,
        query_type="request",
        query_text=query_text,
        matches=matches,
        total_matches=len(matches),
        threshold_used=threshold,
    )


@router.post("/by-rule/{rule_id}", response_model=SemanticSearchResult)
def search_by_rule(
    rule_id: int,
    threshold: float = 0.7,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Find user requests semantically similar to the given physical rule."""
    rule = (
        db.query(PhysicalRule)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .filter(PhysicalRule.rule_id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Physical rule not found")

    # Generate embedding on the fly if missing
    if rule.embedding is None:
        sources = [s.address for s in rule.sources]
        destinations = [d.address for d in rule.destinations]
        text = embedding_service.build_rule_text(
            rule.rule_name, rule.action, sources, destinations, rule.ports
        )
        rule.embedding_text = text
        rule.embedding = embedding_service.embed(text)
        db.commit()

    query_embedding = list(rule.embedding)
    query_text = rule.embedding_text or ""

    distance_expr = Request.embedding.cosine_distance(query_embedding).label("distance")
    rows = (
        db.query(Request, distance_expr)
        .filter(Request.embedding.isnot(None))
        .order_by(distance_expr)
        .limit(limit * 4)
        .all()
    )

    matches = []
    for req, distance in rows:
        score = round(1.0 - distance, 4)
        if score >= threshold:
            data = req.request_json
            matches.append(
                SemanticMatch(
                    request_id=req.request_id,
                    name=req.name,
                    sources=data["sources"],
                    destinations=data["destinations"],
                    ports=data["ports"],
                    similarity_score=score,
                )
            )

    matches = matches[:limit]

    return SemanticSearchResult(
        query_id=rule_id,
        query_type="rule",
        query_text=query_text,
        matches=matches,
        total_matches=len(matches),
        threshold_used=threshold,
    )


@router.post("/by-text", response_model=TextSearchResult)
def search_by_text(payload: TextSearchRequest, db: Session = Depends(get_db)):
    """Free-form text search against rules and/or requests."""
    query_embedding = embedding_service.embed(payload.query)
    matches = []

    if payload.search_in in ("rules", "both"):
        distance_expr = PhysicalRule.embedding.cosine_distance(query_embedding).label("distance")
        rows = (
            db.query(PhysicalRule, distance_expr)
            .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
            .filter(PhysicalRule.embedding.isnot(None))
            .order_by(distance_expr)
            .limit(payload.limit * 4)
            .all()
        )
        for rule, distance in rows:
            score = round(1.0 - distance, 4)
            if score >= payload.threshold:
                sources = [s.address for s in rule.sources]
                destinations = [d.address for d in rule.destinations]
                matches.append(
                    TextSearchMatch(
                        entity_type="rule",
                        rule_id=rule.rule_id,
                        name=rule.rule_name,
                        sources=sources,
                        destinations=destinations,
                        ports=rule.ports,
                        similarity_score=score,
                    )
                )

    if payload.search_in in ("requests", "both"):
        distance_expr = Request.embedding.cosine_distance(query_embedding).label("distance")
        rows = (
            db.query(Request, distance_expr)
            .filter(Request.embedding.isnot(None))
            .order_by(distance_expr)
            .limit(payload.limit * 4)
            .all()
        )
        for req, distance in rows:
            score = round(1.0 - distance, 4)
            if score >= payload.threshold:
                data = req.request_json
                matches.append(
                    TextSearchMatch(
                        entity_type="request",
                        request_id=req.request_id,
                        name=req.name,
                        sources=data["sources"],
                        destinations=data["destinations"],
                        ports=data["ports"],
                        similarity_score=score,
                    )
                )

    matches.sort(key=lambda m: m.similarity_score, reverse=True)
    matches = matches[: payload.limit]

    return TextSearchResult(
        query=payload.query,
        matches=matches,
        total_matches=len(matches),
        threshold_used=payload.threshold,
    )
