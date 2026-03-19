from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Tracker, Game, GameMatch
from app.schemas import TrackerCreate, TrackerOut, GameOut, RunResult
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

    inserted_games = 0
    matched_games = 0

    for item in MOCK_GAMES:
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

    return {
        "tracker_id": tracker.id,
        "inserted_games": inserted_games,
        "matched_games": matched_games,
    }


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