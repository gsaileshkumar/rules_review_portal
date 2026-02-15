from datetime import datetime

from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PhysicalRule(Base):
    __tablename__ = "physical_rules"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    firewall_device: Mapped[str] = mapped_column(String(255), nullable=False)
    ports: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="allow")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sources = relationship("PhysicalRuleSource", back_populates="rule", cascade="all, delete-orphan")
    destinations = relationship("PhysicalRuleDestination", back_populates="rule", cascade="all, delete-orphan")
