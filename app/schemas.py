from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

class TrackerCreate(BaseModel):
    name: str = Field(..., max_length=200, description="Tracker 名稱")
    source: str = Field(default="mock", max_length=50, description="資料來源，例如 mock 或 rawg")
    query_json: str = Field(..., description="追蹤條件 JSON 字串")
    update_frequency: str = Field(default="daily", max_length=20, description="更新頻率：daily / weekly / manual")
    is_active: bool = Field(default=True, description="是否啟用此 tracker")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Games Test",
                "source": "mock",
                "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
                "update_frequency": "daily",
                "is_active": True
            }
        }
    )

    @field_validator("update_frequency")
    @classmethod
    def validate_update_frequency(cls, value: str) -> str:
        allowed = {"daily", "weekly", "manual"}
        value = value.strip().lower()
        if value not in allowed:
            raise ValueError(f"update_frequency must be one of {sorted(allowed)}")
        return value
    
class TrackerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200, description="Tracker 名稱")
    source: str | None = Field(default=None, max_length=50, description="資料來源，例如 mock 或 rawg")
    query_json: str | None = Field(default=None, description="追蹤條件 JSON 字串")
    update_frequency: str | None = Field(default=None, max_length=20, description="更新頻率：daily / weekly / manual")
    is_active: bool | None = Field(default=None, description="是否啟用此 tracker")

    @field_validator("update_frequency")
    @classmethod
    def validate_update_frequency(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = {"daily", "weekly", "manual"}
        value = value.strip().lower()
        if value not in allowed:
            raise ValueError(f"update_frequency must be one of {sorted(allowed)}")
        return value

class TrackerOut(BaseModel):
    id: int
    name: str
    source: str
    query_json: str
    update_frequency: str
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


class LatestRunSummary(BaseModel):
    id: int
    status: str
    started_at: datetime
    ended_at: datetime | None
    inserted_games: int
    matched_games: int
    error_message: str | None


class TrackerSummaryOut(BaseModel):
    tracker_id: int
    name: str
    source: str
    query_json: str
    update_frequency: str
    is_active: bool
    matched_games_count: int
    latest_run: LatestRunSummary | None


class DashboardSummaryOut(BaseModel):
    tracker_count: int
    active_tracker_count: int
    game_count: int
    run_count: int
    daily_active_count: int
    weekly_active_count: int
    latest_run: LatestRunSummary | None

class DashboardActiveTrackerOut(BaseModel):
    id: int
    name: str
    update_frequency: str
    is_active: bool