from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import requests, physical_rules, review, deficiencies
from app.seed import seed_data

app = FastAPI(title="Rules Review Portal", version="0.1.0")

app.include_router(requests.router)
app.include_router(physical_rules.router)
app.include_router(review.router)
app.include_router(deficiencies.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/seed")
def seed(db: Session = Depends(get_db)):
    return seed_data(db)
