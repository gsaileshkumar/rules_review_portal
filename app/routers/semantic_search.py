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


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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

    rules = (
        db.query(PhysicalRule)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .filter(PhysicalRule.embedding.isnot(None))
        .all()
    )

    matches = []
    for rule in rules:
        score = _cosine_similarity(query_embedding, list(rule.embedding))
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
                    similarity_score=round(score, 4),
                )
            )

    matches.sort(key=lambda m: m.similarity_score, reverse=True)
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

    requests = db.query(Request).filter(Request.embedding.isnot(None)).all()

    matches = []
    for req in requests:
        score = _cosine_similarity(query_embedding, list(req.embedding))
        if score >= threshold:
            data = req.request_json
            matches.append(
                SemanticMatch(
                    request_id=req.request_id,
                    name=req.name,
                    sources=data["sources"],
                    destinations=data["destinations"],
                    ports=data["ports"],
                    similarity_score=round(score, 4),
                )
            )

    matches.sort(key=lambda m: m.similarity_score, reverse=True)
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
        rules = (
            db.query(PhysicalRule)
            .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
            .filter(PhysicalRule.embedding.isnot(None))
            .all()
        )
        for rule in rules:
            score = _cosine_similarity(query_embedding, list(rule.embedding))
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
                        similarity_score=round(score, 4),
                    )
                )

    if payload.search_in in ("requests", "both"):
        requests = db.query(Request).filter(Request.embedding.isnot(None)).all()
        for req in requests:
            score = _cosine_similarity(query_embedding, list(req.embedding))
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
                        similarity_score=round(score, 4),
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
