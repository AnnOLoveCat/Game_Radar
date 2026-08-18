import json

from enum import Enum
from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict, StrictBool, computed_field

class TrackerSource(str, Enum):
    mock = "mock"
    rawg = "rawg"


class UpdateFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    manual = "manual"


# =========================
# Current Tracker Query Schemas
# =========================

class TargetGameQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    platform_hints: list[str] = Field(default_factory=list)


# =========================
# Future Development Schemas
# =========================
# These schemas are reserved for future website and review-analysis features.
# They are intentionally not attached to TrackerQueryJson at the current stage.
# Current query_json should only contain basic game lookup data.

class UserReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, max_length=100)
    rating: float | None = Field(default=None, ge=0, le=5)
    review_text: str | None = Field(default=None)
    is_recommended: StrictBool | None = Field(default=None)


class ReviewFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_reviews_limit: int = Field(default=10, ge=1, le=100)
    only_steam_purchase: StrictBool = Field(default=True)
    exclude_received_for_free: StrictBool = Field(default=True)
    min_playtime_at_review_minutes: int = Field(default=0, ge=0)
    sort_by: str = Field(default="weighted_vote_score", max_length=100)


class AnalysisRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_player_experience: StrictBool = Field(default=True)
    detect_low_gameplay_interaction: StrictBool = Field(default=True)
    detect_cinematic_experience: StrictBool = Field(default=True)
    detect_auto_play_or_lack_of_control: StrictBool = Field(default=True)
    compare_media_and_player_reviews: StrictBool = Field(default=True)
    do_not_use_media_score_as_main_score: StrictBool = Field(default=True)
class TrackerQueryJson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_game: TargetGameQuery | None = Field(
        default=None,
        description="Main game target for tracking. Prefer this field for new tracker query data."
    )
    sources_to_check: list[str] = Field(default_factory=list)
    regions: list[str] = Field(
        default_factory=list,
        description="Legacy field. Kept for backward compatibility and not used as a primary matching condition."
    )
    genres: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)

    # legacy-compatible fields
    games: list[str] = Field(
        default_factory=list,
        description="Legacy field. Prefer target_game.title for single-game tracking."
    )
    is_indie: StrictBool = Field(
        default=False,
        description="Legacy field. Kept for backward compatibility."
    )
    studios: list[str] = Field(
        default_factory=list,
        description="Legacy field. Kept for backward compatibility."
    )

class TrackerCreate(BaseModel):
    name: str = Field(..., max_length=200, description="Tracker 名稱")
    source: TrackerSource = Field(default=TrackerSource.mock, description="資料來源：mock / rawg")
    query_json: TrackerQueryJson = Field(..., description="追蹤條件 JSON 物件")
    update_frequency: UpdateFrequency = Field(
        default=UpdateFrequency.daily,
        description="更新頻率：daily / weekly / manual"
    )
    is_active: bool = Field(default=True, description="是否啟用此 tracker")

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "name": "Games Test",
                "source": "mock",
                "update_frequency": "daily",
                "is_active": True,
                "query_json": {
                    "target_game": {
                        "title": "Mixtape",
                        "platform_hints": ["Steam", "PC", "Xbox"]
                    },
                    "sources_to_check": [
                        "steam",
                        "rawg",
                        "igdb",
                        "opencritic",
                        "metacritic"
                    ],
                    "genres": ["Adventure", "Indie", "Narrative"],
                    "platforms": ["PC", "Steam", "Xbox"],
                }
            }
        }
    )


class TrackerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200, description="Tracker 名稱")
    source: TrackerSource | None = Field(default=None, description="資料來源：mock / rawg")
    query_json: TrackerQueryJson | None = Field(default=None, description="追蹤條件 JSON 物件")
    update_frequency: UpdateFrequency | None = Field(default=None, description="更新頻率：daily / weekly / manual")
    is_active: bool | None = Field(default=None, description="是否啟用此 tracker")

    model_config = ConfigDict(use_enum_values=True)


class TrackerOut(BaseModel):
    id: int
    name: str
    source: str
    query_json: dict[str, Any]
    update_frequency: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("query_json", mode="before")
    @classmethod
    def parse_query_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)

        return value


class GameOut(BaseModel):
    id: int
    external_id: str
    title: str

    studio: str | None = Field(
        default=None,
        description="Developer or game studio."
    )
    publisher: str | None = Field(
        default=None,
        description="Game publisher."
    )

    genre: str | None = None
    platform: str | None = None
    release_date: str | None = None
    latest_update_date: str | None = None
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunResult(BaseModel):
    tracker_id: int
    inserted_games: int
    matched_games: int


class RunOut(BaseModel):
    id: int
    tracker_id: int
    started_at: datetime = Field(exclude=True)
    ended_at: datetime | None = Field(default=None, exclude=True)
    status: str
    inserted_games: int
    matched_games: int
    error_message: str | None = None

    @computed_field
    @property
    def check_time(self) -> datetime:
        return self.started_at

    model_config = ConfigDict(from_attributes=True)


class LatestRunSummary(BaseModel):
    id: int
    status: str
    started_at: datetime = Field(exclude=True)
    ended_at: datetime | None = Field(default=None, exclude=True)
    inserted_games: int
    matched_games: int
    error_message: str | None = None

    @computed_field
    @property
    def check_time(self) -> datetime:
        return self.started_at

    model_config = ConfigDict(from_attributes=True)


class TrackerSummaryOut(BaseModel):
    tracker_id: int
    name: str
    source: str
    query_json: dict[str, Any]
    update_frequency: str
    is_active: bool
    matched_games_count: int
    latest_run: LatestRunSummary | None

    @field_validator("query_json", mode="before")
    @classmethod
    def parse_query_json(cls, value):
        if isinstance(value, str):
            return json.loads(value)

        return value


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

class SchedulerJobOut(BaseModel):
    id: str
    next_run_time: str | None
    trigger: str


class SchedulerStatusOut(BaseModel):
    scheduler_running: bool
    job_count: int
    jobs: list[SchedulerJobOut]

class BatchRunResultOut(BaseModel):
    tracker_id: int
    name: str
    status: str
    inserted_games: int
    matched_games: int
    error: str | None