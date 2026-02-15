from datetime import datetime

from pydantic import BaseModel


class RequestJsonSchema(BaseModel):
    sources: list[str]
    destinations: list[str]
    ports: list[str]


class RequestCreate(BaseModel):
    name: str
    request_json: RequestJsonSchema


class RequestResponse(BaseModel):
    request_id: int
    name: str
    status: str
    request_json: RequestJsonSchema
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
