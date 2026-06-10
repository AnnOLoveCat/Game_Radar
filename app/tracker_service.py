import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Tracker, Game, GameMatch, Run
from app.match_service import match_game
from app.fetch_service import fetch_games_by_source

def create_tracker_record(payload, db:Session):
    try:
        query = json.loads(payload.query_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid query_json format")

    if not isinstance(query, dict):
        raise HTTPException(status_code=400, detail="query_json must be a JSON object")

    allowed_keys = {"regions", "games", "is_indie", "studios"}
    unexpected_keys = set(query.keys()) - allowed_keys
    if unexpected_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported query_json keys: {sorted(unexpected_keys)}"
        )

    if "regions" in query and not isinstance(query["regions"], list):
        raise HTTPException(status_code=400, detail="regions must be a list")

    if "games" in query and not isinstance(query["games"], list):
        raise HTTPException(status_code=400, detail="games must be a list")

    if "studios" in query and not isinstance(query["studios"], list):
        raise HTTPException(status_code=400, detail="studios must be a list")

    if "is_indie" in query and not isinstance(query["is_indie"], bool):
        raise HTTPException(status_code=400, detail="is_indie must be a boolean")

    tracker = Tracker(
        name=payload.name,
        source=payload.source,
        query_json=payload.query_json,
        update_frequency=payload.update_frequency,
        is_active=payload.is_active,
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)
    return tracker


def execute_tracker_run(tracker: Tracker, db: Session):
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
        
        games_data = fetch_games_by_source(tracker.source, query)
        for item in games_data:
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
    

def delete_tracker_with_dependencies(tracker: Tracker, db: Session):
    db.query(GameMatch).filter(GameMatch.tracker_id == tracker.id).delete()
    db.query(Run).filter(Run.tracker_id == tracker.id).delete()

    db.delete(tracker)
    db.commit()

    return {"message": "Tracker deleted successfully"}


def update_tracker_fields(tracker: Tracker, update_data: dict, db: Session):
    for field, value in update_data.items():
        setattr(tracker, field, value)

    db.commit()
    db.refresh(tracker)
    return tracker


def get_tracker_or_404(tracker_id: int, db: Session):
    tracker = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")
    return tracker

def list_all_trackers(db: Session):
    return db.query(Tracker).order_by(Tracker.id.desc()).all()

def list_all_runs(db: Session):
    return db.query(Run).order_by(Run.id.desc()).all()

def list_all_games(db: Session):
    return db.query(Game).order_by(Game.id.desc()).all()


# 查tracker的執行紀錄
def list_runs_by_tracker(tracker_id: int, db: Session):
    return(
        db.query(Run)
        .filter(Run.tracker_id==tracker_id)
        .order_by(Run.id.desc())
        .all()
    )


# 查tracker配對到的遊戲
def list_games_by_tracker(tracker_id: int, db: Session):
    return(
        db.query(Game)
        .join(GameMatch, Game.id == GameMatch.game_id)
        .filter(GameMatch.tracker_id == tracker_id)
        .order_by(Game.id.desc())
        .all()
    )

def get_tracker_detail(tracker_id: int, db: Session):
    return get_tracker_or_404(tracker_id, db)

def list_active_trackers_by_frequency(update_frequency: str, db: Session):
    return (
        db.query(Tracker).filter(
            Tracker.is_active == True,
            Tracker.update_frequency == update_frequency
        ).all()
    )

def run_trackers_by_frequency(update_frequency: str, db: Session):
    trackers = list_active_trackers_by_frequency(update_frequency, db)

    results = []
    for tracker in trackers:
        try:
            result = execute_tracker_run(tracker, db)
            results.append({
                "tracker_id": tracker.id,
                "name": tracker.name,
                "status": "success",
                "inserted_games": result["inserted_games"],
                "matched_games": result["matched_games"],
                "error": None,
            })
        except HTTPException as e:
            results.append({
                "tracker_id": tracker.id,
                "name": tracker.name,
                "status": "failed",
                "inserted_games": 0,
                "matched_games": 0,
                "error": e.detail,
            })
        except Exception as e:
            results.append({
                "tracker_id": tracker.id,
                "name": tracker.name,
                "status": "failed",
                "inserted_games": 0,
                "matched_games": 0,
                "error": str(e),
            })

    return results

def get_tracker_summary(tracker_id: int, db: Session):
    tracker = get_tracker_or_404(tracker_id, db)

    latest_run = (
        db.query(Run)
        .filter(Run.tracker_id == tracker_id)
        .order_by(Run.id.desc())
        .first()
    )

    matched_games_count = (
        db.query(GameMatch)
        .filter(GameMatch.tracker_id == tracker_id)
        .count()
    )

    return {
        "tracker": tracker,
        "latest_run": latest_run,
        "matched_games_count": matched_games_count,
    }