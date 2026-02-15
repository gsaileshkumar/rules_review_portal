from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.physical_rule import PhysicalRule
from app.models.request import Request
from app.schemas.semantic_search import EmbeddingGenerateResult, EmbeddingStatus
from app.services import embedding_service

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


@router.get("/status", response_model=EmbeddingStatus)
def get_embedding_status(db: Session = Depends(get_db)):
    """Return embedding coverage statistics."""
    total_requests = db.query(Request).count()
    requests_with_embeddings = db.query(Request).filter(Request.embedding.isnot(None)).count()
    total_rules = db.query(PhysicalRule).count()
    rules_with_embeddings = db.query(PhysicalRule).filter(PhysicalRule.embedding.isnot(None)).count()

    return EmbeddingStatus(
        total_requests=total_requests,
        requests_with_embeddings=requests_with_embeddings,
        total_rules=total_rules,
        rules_with_embeddings=rules_with_embeddings,
    )


@router.post("/generate", response_model=EmbeddingGenerateResult)
def generate_embeddings(force: bool = False, db: Session = Depends(get_db)):
    """Batch generate embeddings for all requests and physical rules.

    Args:
        force: If True, regenerate embeddings even for records that already have them.
    """
    requests_generated = 0
    requests_skipped = 0
    rules_generated = 0
    rules_skipped = 0

    # Generate embeddings for all requests
    requests = db.query(Request).all()
    for req in requests:
        if req.embedding is not None and not force:
            requests_skipped += 1
            continue
        data = req.request_json
        text = embedding_service.build_request_text(
            req.name, data["sources"], data["destinations"], data["ports"]
        )
        req.embedding_text = text
        req.embedding = embedding_service.embed(text)
        requests_generated += 1

    # Generate embeddings for all physical rules
    rules = (
        db.query(PhysicalRule)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .all()
    )
    for rule in rules:
        if rule.embedding is not None and not force:
            rules_skipped += 1
            continue
        sources = [s.address for s in rule.sources]
        destinations = [d.address for d in rule.destinations]
        text = embedding_service.build_rule_text(
            rule.rule_name, rule.action, sources, destinations, rule.ports
        )
        rule.embedding_text = text
        rule.embedding = embedding_service.embed(text)
        rules_generated += 1

    db.commit()

    return EmbeddingGenerateResult(
        requests_generated=requests_generated,
        rules_generated=rules_generated,
        requests_skipped=requests_skipped,
        rules_skipped=rules_skipped,
    )
