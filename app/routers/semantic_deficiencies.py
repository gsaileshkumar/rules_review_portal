from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.semantic_deficiency import SemanticDeficiency
from app.schemas.semantic_search import SemanticDeficiencyResponse

router = APIRouter(prefix="/api/semantic-deficiencies", tags=["semantic-deficiencies"])


@router.get("", response_model=list[SemanticDeficiencyResponse])
def list_semantic_deficiencies(type: str | None = None, db: Session = Depends(get_db)):
    """List all semantic deficiencies, optionally filtered by type."""
    query = db.query(SemanticDeficiency)
    if type:
        query = query.filter(SemanticDeficiency.type == type)
    return query.order_by(SemanticDeficiency.created_at.desc()).all()


@router.get("/{deficiency_id}", response_model=SemanticDeficiencyResponse)
def get_semantic_deficiency(deficiency_id: int, db: Session = Depends(get_db)):
    """Get a single semantic deficiency by ID."""
    deficiency = db.query(SemanticDeficiency).filter(SemanticDeficiency.id == deficiency_id).first()
    if not deficiency:
        raise HTTPException(status_code=404, detail="Semantic deficiency not found")
    return deficiency
