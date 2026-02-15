from datetime import datetime

from pydantic import BaseModel


class DeficiencyResponse(BaseModel):
    deficiency_id: int
    type: str
    request_id: int | None
    rule_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
