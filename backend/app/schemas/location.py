from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    parent_id: int | None = None
    level: str = Field(pattern="^(province|district|neighborhood)$")
    name: str = Field(min_length=1, max_length=150)
    normalized_name: str = Field(min_length=1, max_length=150)
    external_code: str | None = Field(default=None, max_length=50)


class LocationRead(LocationCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
