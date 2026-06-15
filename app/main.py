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
    get_tracker_summary,
    get_dashboard_summary,
    get_recent_runs,
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


@app.get("/v1/scheduler/status")
def get_scheduler_status():
    jobs = scheduler.get_jobs()

    return {
        "scheduler_running": scheduler.running,
        "job_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ],

        # jobs寫法等同下面
        # job_list = []

        # for job in jobs:
        #     job_list.append(
        #         {
        #             "id": job.id,
        #             "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        #             "trigger": str(job.trigger),
        #         }
        #     )
    }


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


@app.get("/v1/trackers/{tracker_id}/summary")
def get_tracker_summary_api(tracker_id: int, db: Session = Depends(get_db)):
    summary = get_tracker_summary(tracker_id, db)

    tracker = summary["tracker"]
    latest_run = summary["latest_run"]

    return {
        "tracker_id": tracker.id,
        "name": tracker.name,
        "source": tracker.source,
        "query_json": tracker.query_json,
        "update_frequency": tracker.update_frequency,
        "is_active": tracker.is_active,
        "matched_games_count": summary["matched_games_count"],
        "latest_run": {
            "id": latest_run.id,
            "status": latest_run.status,
            "started_at": latest_run.started_at,
            "ended_at": latest_run.ended_at,
            "inserted_games": latest_run.inserted_games,
            "matched_games": latest_run.matched_games,
            "error_message": latest_run.error_message,
        } if latest_run else None,
    }


@app.get("/v1/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    return get_dashboard_summary(db)


@app.get("/v1/dashboard/recent-runs")
def dashboard_recent_runs(limit: int = 5, db: Session = Depends(get_db)):
    return get_recent_runs(limit, db)

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
