from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.review import ReviewResult
from app.schemas.semantic_search import SemanticReviewResult
from app.services.review_service import run_review
from app.services.semantic_review_service import run_semantic_review

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/run", response_model=ReviewResult)
def trigger_review(db: Session = Depends(get_db)):
    return run_review(db)


@router.post("/run-semantic", response_model=SemanticReviewResult)
def trigger_semantic_review(threshold: float | None = None, db: Session = Depends(get_db)):
    """Run a semantic similarity-based review.

    Uses vector embeddings (qwen3-embedding via Ollama) to match physical rules
    with user requests, tolerating format variations like CIDR vs IP range notation.

    Args:
        threshold: Minimum cosine similarity score (0.0-1.0) to consider a match.
                   Defaults to the configured SIMILARITY_THRESHOLD (0.7).
    """
    return run_semantic_review(db, threshold)
