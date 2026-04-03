from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.db import get_db
from app.models import Tracker, Game, GameMatch, Run
from app.schemas import TrackerCreate, TrackerUpdate, TrackerOut, GameOut, RunResult, RunOut
from app.mock_data import MOCK_GAMES

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


@app.post("/v1/trackers/{tracker_id}/run", response_model=RunResult)
def run_tracker(tracker_id: int, db: Session = Depends(get_db)):
    tracker = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    run = Run(tracker_id=tracker.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    inserted_games = 0
    matched_games = 0

    try:
        try:
            query = json.loads(tracker.query_json)
        except json.JSONDecodeError:
            run.ended_at = datetime.utcnow()
            run.status = "failed"
            run.error_message = "Invalid query_json format"
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid query_json format")

        for item in MOCK_GAMES:
            if not match_game(item, query):
                continue

            game = db.query(Game).filter(Game.external_id == item["external_id"]).first()

            if not game:
                game = Game(**item)
                db.add(game)
                db.commit()
                db.refresh(game)
                inserted_games += 1

            existing_match = (
                db.query(GameMatch)
                .filter(GameMatch.tracker_id == tracker.id, GameMatch.game_id == game.id)
                .first()
            )

            if not existing_match:
                match = GameMatch(tracker_id=tracker.id, game_id=game.id, score=1)
                db.add(match)
                db.commit()
                matched_games += 1

        run.ended_at = datetime.utcnow()
        run.status = "success"
        run.inserted_games = inserted_games
        run.matched_games = matched_games
        db.commit()

        return {
            "tracker_id": tracker.id,
            "inserted_games": inserted_games,
            "matched_games": matched_games,
        }

    except HTTPException:
        raise
    except Exception as e:
        run.ended_at = datetime.utcnow()
        run.status = "failed"
        run.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Run failed: {str(e)}")

@app.get("/v1/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    return db.query(Run).order_by(Run.id.desc()).all()


@app.get("/v1/trackers/{tracker_id}/runs", response_model=list[RunOut])
def list_tracker_runs(tracker_id: int, db: Session = Depends(get_db)):
    tracker = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    return (
        db.query(Run)
        .filter(Run.tracker_id == tracker_id)
        .order_by(Run.id.desc())
        .all()
    )

@app.patch("/v1/trackers/{tracker_id}", response_model=TrackerOut)
def update_tracker(tracker_id: int, payload: TrackerUpdate, db: Session = Depends(get_db)):
    tracker = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(tracker, field, value)

    db.commit()
    db.refresh(tracker)
    return tracker

@app.delete("/v1/trackers/{tracker_id}")
def delete_tracker(tracker_id: int, db: Session = Depends(get_db)):
    tracker = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    db.query(GameMatch).filter(GameMatch.tracker_id == tracker_id).delete()
    db.query(Run).filter(Run.tracker_id == tracker_id).delete()

    db.delete(tracker)
    db.commit()
    return {"message": "Tracker deleted successfully"}

@app.get("/v1/games", response_model=list[GameOut])
def list_games(db: Session = Depends(get_db)):
    return db.query(Game).order_by(Game.id.desc()).all()


@app.get("/v1/trackers/{tracker_id}/games", response_model=list[GameOut])
def list_tracker_games(tracker_id: int, db: Session = Depends(get_db)):
    tracker = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    games = (
        db.query(Game)
        .join(GameMatch, Game.id == GameMatch.game_id)
        .filter(GameMatch.tracker_id == tracker_id)
        .order_by(Game.id.desc())
        .all()
    )
    return games

def match_game(item, query):
    focus = query.get("focus")

    valid_focus = {"asia", "game", "indie"}
    if focus not in valid_focus:
        return False

    # 亞洲遊戲
    if focus == "asia":
        regions = query.get("regions", [])
        if item.get("region") not in regions:
            return False

    # 指定遊戲
    if focus == "game":
        games = query.get("games", [])
        if item.get("title") not in games:
            return False

    # Indie
    if focus == "indie":
        studio = item.get("studio", "").lower()
        if "indie" not in studio and "studio" not in studio:
            return False

    return True