from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Tracker
from app.schemas import TrackerCreate, TrackerOut

app = FastAPI(title="Game Radar", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/trackers", response_model=TrackerOut)
def create_tracker(payload: TrackerCreate, db: Session = Depends(get_db)):
    tracker = Tracker(
        name=payload.name,
        source=payload.source,
        query_json=payload.query_json,
        schedule=payload.schedule,
        is_enabled=payload.is_enabled,
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)
    return tracker


@app.get("/v1/trackers", response_model=list[TrackerOut])
def list_trackers(db: Session = Depends(get_db)):
    return db.query(Tracker).order_by(Tracker.id.desc()).all()