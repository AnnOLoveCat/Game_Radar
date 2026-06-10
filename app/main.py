from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from app.db import SessionLocal

from app.db import get_db
from app.models import Tracker, Game, GameMatch, Run
from app.schemas import TrackerCreate, TrackerUpdate, TrackerOut, GameOut, RunResult, RunOut
from app.tracker_service import (
    create_tracker_record,
    execute_tracker_run,
    delete_tracker_with_dependencies,
    update_tracker_fields,
    get_tracker_or_404,
    list_all_trackers,
    list_all_runs,
    list_all_games,
    list_runs_by_tracker,
    list_games_by_tracker,
    get_tracker_detail,
    run_trackers_by_frequency,
    list_active_trackers_by_frequency,
)

# app = FastAPI(title="Game Radar", version="0.1.0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_daily_trackers,
        "cron",
        hour=9,
        minute=0,
        id="daily_trackers",
        replace_existing=True,
    )
    scheduler.add_job(
        run_weekly_trackers,
        "cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="weekly_trackers",
        replace_existing=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(title="Game Radar", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/trackers", response_model=TrackerOut)
def create_tracker(payload: TrackerCreate, db: Session = Depends(get_db)):
    return create_tracker_record(payload, db)


@app.delete("/v1/trackers/{tracker_id}")
def delete_tracker(tracker_id: int, db: Session = Depends(get_db)):
    tracker = get_tracker_or_404(tracker_id, db)
    return delete_tracker_with_dependencies(tracker, db)


@app.get("/v1/trackers", response_model=list[TrackerOut])
def list_trackers(db: Session = Depends(get_db)):
    return list_all_trackers(db)


@app.post("/v1/trackers/{tracker_id}/run", response_model=RunResult)
def run_tracker(tracker_id: int, db: Session = Depends(get_db)):
    tracker = get_tracker_or_404(tracker_id, db)
    return execute_tracker_run(tracker, db)


@app.get("/v1/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    return list_all_runs(db)


@app.get("/v1/trackers/{tracker_id}/runs", response_model=list[RunOut])
def list_tracker_runs(tracker_id: int, db: Session = Depends(get_db)):

    get_tracker_or_404(tracker_id, db)
    return list_runs_by_tracker(tracker_id, db)


@app.get("/v1/trackers/{tracker_id}/games", response_model=list[GameOut])
def list_tracker_games(tracker_id: int, db: Session = Depends(get_db)):
    
    get_tracker_or_404(tracker_id, db)
    return list_games_by_tracker(tracker_id, db)


@app.patch("/v1/trackers/{tracker_id}", response_model=TrackerOut)
def update_tracker(tracker_id: int, payload: TrackerUpdate, db: Session = Depends(get_db)):
    tracker = get_tracker_or_404(tracker_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    return update_tracker_fields(tracker, update_data, db)


@app.get("/v1/games", response_model=list[GameOut])
def list_games(db: Session = Depends(get_db)):
    return list_all_games(db)


@app.post("/v1/trackers/run/{update_frequency}")
def run_trackers_by_update_frequency(update_frequency: str, db: Session = Depends(get_db)):
    return run_trackers_by_frequency(update_frequency, db)


@app.get("/v1/trackers/active/{update_frequency}", response_model=list[TrackerOut])
def list_active_trackers(update_frequency: str, db: Session = Depends(get_db)):
    return list_active_trackers_by_frequency(update_frequency, db)


@app.get("/v1/trackers/{tracker_id}", response_model=TrackerOut)
def get_tracker(tracker_id: int, db: Session = Depends(get_db)):
    return get_tracker_detail(tracker_id, db)


scheduler = BackgroundScheduler()

def run_daily_trackers():
    db = SessionLocal()
    try:
        run_trackers_by_frequency("daily", db)
    finally:
        db.close()


def run_weekly_trackers():
    db = SessionLocal()
    try:
        run_trackers_by_frequency("weekly", db)
    finally:
        db.close()
