from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.physical_rule import PhysicalRule
from app.models.physical_rule_source import PhysicalRuleSource
from app.models.physical_rule_destination import PhysicalRuleDestination
from app.schemas.physical_rule import PhysicalRuleCreate, PhysicalRuleResponse

router = APIRouter(prefix="/api/physical-rules", tags=["physical-rules"])


@router.post("", response_model=PhysicalRuleResponse)
def create_physical_rule(payload: PhysicalRuleCreate, db: Session = Depends(get_db)):
    rule = PhysicalRule(
        rule_name=payload.rule_name,
        firewall_device=payload.firewall_device,
        ports=payload.ports,
        action=payload.action,
    )
    for addr in payload.sources:
        rule.sources.append(PhysicalRuleSource(address=addr))
    for addr in payload.destinations:
        rule.destinations.append(PhysicalRuleDestination(address=addr))

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("", response_model=list[PhysicalRuleResponse])
def list_physical_rules(db: Session = Depends(get_db)):
    return (
        db.query(PhysicalRule)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .all()
    )


@router.get("/{rule_id}", response_model=PhysicalRuleResponse)
def get_physical_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = (
        db.query(PhysicalRule)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .filter(PhysicalRule.rule_id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Physical rule not found")
    return rule
