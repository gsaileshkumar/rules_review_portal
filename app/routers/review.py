from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.review import ReviewResult
from app.services.review_service import run_review

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/run", response_model=ReviewResult)
def trigger_review(db: Session = Depends(get_db)):
    return run_review(db)
