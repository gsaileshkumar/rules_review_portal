from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SemanticDeficiency(Base):
    __tablename__ = "semantic_deficiencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    request_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    best_match_request_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    best_match_rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
