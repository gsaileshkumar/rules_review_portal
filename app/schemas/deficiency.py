from datetime import datetime

from pydantic import BaseModel


class DeficiencyDetails(BaseModel):
    sources: list[str]
    destinations: list[str]
    ports: list[str]


class DeficiencyResponse(BaseModel):
    deficiency_id: int
    type: str
    request_id: int | None
    rule_id: int | None
    details: DeficiencyDetails
    created_at: datetime

    model_config = {"from_attributes": True}
