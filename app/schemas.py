from datetime import datetime
from pydantic import BaseModel, Field

class TrackerCreate(BaseModel):
    name: str = Field(..., max_length=200)
    source: str = Field(default="mixed", max_length=50)
    query_json: str
    schedule: str = Field(default="daily", max_length=20)
    is_active: bool = True

class TrackerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=50)
    query_json: str | None = None
    schedule: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

class TrackerOut(BaseModel):
    id: int
    name: str
    source: str
    query_json: str
    schedule: str
    is_active: bool
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
    latest_update_date: str | None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class RunResult(BaseModel):
    tracker_id: int
    inserted_games: int
    matched_games: int


class RunOut(BaseModel):
    id: int
    tracker_id: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    inserted_games: int
    matched_games: int
    error_message: str | None

    class Config:
        from_attributes = True