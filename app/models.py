from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Tracker(Base):
    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="openalex")
    query_json: Mapped[str] = mapped_column(Text, nullable=False)
    schedule: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    studio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latest_update_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class GameMatch(Base):
    __tablename__ = "game_matches"
    __table_args__ = (
        UniqueConstraint("tracker_id", "game_id", name="uq_tracker_game_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    inserted_games: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_games: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)