from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PhysicalRuleSource(Base):
    __tablename__ = "physical_rule_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("physical_rules.rule_id"), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    rule = relationship("PhysicalRule", back_populates="sources")
