from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.deficiency import Deficiency
from app.schemas.deficiency import DeficiencyResponse

router = APIRouter(prefix="/api/deficiencies", tags=["deficiencies"])


@router.get("", response_model=list[DeficiencyResponse])
def list_deficiencies(type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Deficiency)
    if type:
        query = query.filter(Deficiency.type == type)
    return query.all()


@router.get("/{deficiency_id}", response_model=DeficiencyResponse)
def get_deficiency(deficiency_id: int, db: Session = Depends(get_db)):
    deficiency = db.query(Deficiency).filter(Deficiency.deficiency_id == deficiency_id).first()
    if not deficiency:
        raise HTTPException(status_code=404, detail="Deficiency not found")
    return deficiency
