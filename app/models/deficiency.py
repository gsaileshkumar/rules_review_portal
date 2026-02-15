from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Deficiency(Base):
    __tablename__ = "deficiencies"

    deficiency_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    request_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("requests.request_id"), nullable=True)
    rule_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("physical_rules.rule_id"), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request = relationship("Request")
    rule = relationship("PhysicalRule")
