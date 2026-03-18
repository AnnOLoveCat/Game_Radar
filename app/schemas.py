from datetime import datetime
from pydantic import BaseModel, Field

class TrackerCreate(BaseModel):
    name: str = Field(..., max_length=200)
    source: str = Field(default="mixed", max_length=50)
    query_json: str
    schedule: str = Field(default="daily", max_length=20)
    is_enabled: bool = True

class TrackerOut(BaseModel):
    id: int
    name: str
    source: str
    query_json: str
    schedule: str
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True