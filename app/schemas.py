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


class GameOut(BaseModel):
    id: int
    external_id: str
    title: str
    studio: str | None
    region: str | None
    genre: str | None
    platform: str | None
    release_date: str | None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class RunResult(BaseModel):
    tracker_id: int
    inserted_games: int
    matched_games: int