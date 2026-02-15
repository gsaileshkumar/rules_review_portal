from datetime import datetime

from pydantic import BaseModel


class PhysicalRuleCreate(BaseModel):
    rule_name: str
    firewall_device: str
    ports: list[str]
    action: str = "allow"
    sources: list[str]
    destinations: list[str]


class PhysicalRuleSourceResponse(BaseModel):
    id: int
    address: str

    model_config = {"from_attributes": True}


class PhysicalRuleDestinationResponse(BaseModel):
    id: int
    address: str

    model_config = {"from_attributes": True}


class PhysicalRuleResponse(BaseModel):
    rule_id: int
    rule_name: str
    firewall_device: str
    ports: list[str]
    action: str
    created_at: datetime
    sources: list[PhysicalRuleSourceResponse]
    destinations: list[PhysicalRuleDestinationResponse]

    model_config = {"from_attributes": True}
