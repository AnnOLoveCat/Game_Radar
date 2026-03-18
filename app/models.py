from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.db import Base

class Tracker(Base):
    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="openalex")
    query_json: Mapped[str] = mapped_column(Text, nullable=False)  # 先用 Text 存 query_json，這樣 SQLite/PG 都通用；未來升級 PG 再轉 JSONB。
    schedule: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)