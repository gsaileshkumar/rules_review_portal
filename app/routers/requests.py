from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.request import Request
from app.schemas.request import RequestCreate, RequestResponse
from app.services import embedding_service

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.post("", response_model=RequestResponse)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    data = payload.request_json.model_dump()
    req = Request(name=payload.name, request_json=data)
    text = embedding_service.build_request_text(
        payload.name, data["sources"], data["destinations"], data["ports"]
    )
    req.embedding_text = text
    req.embedding = embedding_service.embed(text)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=list[RequestResponse])
def list_requests(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Request)
    if status:
        query = query.filter(Request.status == status)
    return query.all()


@router.get("/{request_id}", response_model=RequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db)):
    req = db.query(Request).filter(Request.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req
