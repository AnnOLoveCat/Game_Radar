import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Tracker, Game, GameMatch, Run

from app.match_service import match_game
from app.fetch_service import fetch_games_by_source
from app.error_service import (
    raise_expected_boolean,
    raise_expected_list,
    raise_expected_object,
    raise_query_json_error,
    raise_run_execution_error,
    raise_run_query_json_format_error,
    raise_unsupported_query_json_keys,
    raise_tracker_not_found,
)


def validate_tracker_query_json(query: dict):
    if not isinstance(query, dict):
        raise_query_json_error("query_json must be a JSON object")

    allowed_keys = {
        "target_game",
        "sources_to_check",
        "regions",
        "genres",
        "platforms",
        "user_review",
        "review_filters",
        "analysis_rules",

        # legacy-compatible fields
        "games",
        "is_indie",
        "studios",
    }

    unexpected_keys = set(query.keys()) - allowed_keys

    if unexpected_keys:
        raise_unsupported_query_json_keys(unexpected_keys)

    if "target_game" in query and not isinstance(query["target_game"], dict):
        raise_expected_object("target_game")

    if "sources_to_check" in query and not isinstance(query["sources_to_check"], list):
        raise_expected_list("sources_to_check")

    if "regions" in query and not isinstance(query["regions"], list):
        raise_expected_list("regions")

    if "genres" in query and not isinstance(query["genres"], list):
        raise_expected_list("genres")

    if "platforms" in query and not isinstance(query["platforms"], list):
        raise_expected_list("platforms")

    if "user_review" in query and not isinstance(query["user_review"], dict):
        raise_expected_object("user_review")

    if "review_filters" in query and not isinstance(query["review_filters"], dict):
        raise_expected_object("review_filters")

    if "analysis_rules" in query and not isinstance(query["analysis_rules"], dict):
        raise_expected_object("analysis_rules")

    if "games" in query and not isinstance(query["games"], list):
        raise_expected_list("games")

    if "studios" in query and not isinstance(query["studios"], list):
        raise_expected_list("studios")

    if "is_indie" in query and not isinstance(query["is_indie"], bool):
        raise_expected_boolean("is_indie")


def _to_plain_value(value):
    if hasattr(value, "value"):
        return value.value

    return value

def _to_plain_dict(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()

    return value

def create_tracker_record(payload, db: Session):
    query = _to_plain_dict(payload.query_json)

    validate_tracker_query_json(query)

    tracker = Tracker(
        name=payload.name,
        source=_to_plain_value(payload.source),
        query_json=json.dumps(query, ensure_ascii=False),
        update_frequency=_to_plain_value(payload.update_frequency),
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
            raise_run_query_json_format_error()
        
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

    except HTTPException as error:
        run.ended_at = datetime.utcnow()
        run.status = "failed"
        run.error_message = str(error.detail)
        db.commit()
        raise
    except Exception as e:
        run.ended_at = datetime.utcnow()
        run.status = "failed"
        run.error_message = str(e)
        db.commit()
        raise_run_execution_error(str(e))
    

def delete_tracker_with_dependencies(tracker: Tracker, db: Session):
    db.query(GameMatch).filter(GameMatch.tracker_id == tracker.id).delete()
    db.query(Run).filter(Run.tracker_id == tracker.id).delete()

    db.delete(tracker)
    db.commit()

    return {"message": "Tracker deleted successfully"}


def update_tracker_fields(tracker: Tracker, update_data: dict, db: Session):
    if "query_json" in update_data:
        query = _to_plain_dict(update_data["query_json"])
        validate_tracker_query_json(query)
        update_data["query_json"] = json.dumps(query, ensure_ascii=False)

    for field, value in update_data.items():
        if field in {"source", "update_frequency"}:
            setattr(tracker, field, _to_plain_value(value))
        else:
            setattr(tracker, field, value)

    db.commit()
    db.refresh(tracker)
    return tracker


def get_tracker_or_404(tracker_id: int, db: Session) -> Tracker:
    tracker = db.get(Tracker, tracker_id)

    if tracker is None:
        raise_tracker_not_found()

    return tracker

def list_all_trackers(db: Session):
    return db.query(Tracker).order_by(Tracker.id.desc()).all()

def list_all_runs(db: Session):
    return db.query(Run).order_by(Run.id.desc()).all()

def list_all_games(db: Session):
    return db.query(Game).order_by(Game.id.desc()).all()


# 查tracker的執行紀錄
def list_runs_by_tracker(tracker_id: int, db: Session):
    get_tracker_or_404(tracker_id, db)

    return (
        db.query(Run)
        .filter(Run.tracker_id == tracker_id)
        .order_by(Run.id.desc())
        .all()
    )

# 查tracker配對到的遊戲
def list_games_by_tracker(tracker_id: int, db: Session):
    get_tracker_or_404(tracker_id, db)

    return (
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
        db.query(Tracker)
        .filter(
            Tracker.is_active == True,
            Tracker.update_frequency == update_frequency
        )
        .all()
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


def get_dashboard_summary(db: Session):
    tracker_count = db.query(Tracker).count()
    active_tracker_count = db.query(Tracker).filter(Tracker.is_active == True).count()
    game_count = db.query(Game).count()
    run_count = db.query(Run).count()

    latest_run = (
        db.query(Run)
        .order_by(Run.id.desc())
        .first()
    )

    daily_active_count = (
        db.query(Tracker)
        .filter(
            Tracker.is_active == True,
            Tracker.update_frequency == "daily"
        )
        .count()
    )

    weekly_active_count = (
        db.query(Tracker)
        .filter(
            Tracker.is_active == True,
            Tracker.update_frequency == "weekly"
        )
        .count()
    )

    return {
        "tracker_count": tracker_count,
        "active_tracker_count": active_tracker_count,
        "game_count": game_count,
        "run_count": run_count,
        "daily_active_count": daily_active_count,
        "weekly_active_count": weekly_active_count,
        "latest_run": {
            "id": latest_run.id,
            "tracker_id": latest_run.tracker_id,
            "status": latest_run.status,
            "started_at": latest_run.started_at,
            "ended_at": latest_run.ended_at,
            "inserted_games": latest_run.inserted_games,
            "matched_games": latest_run.matched_games,
            "error_message": latest_run.error_message,
        } if latest_run else None,
    }


def get_recent_runs(limit: int, db: Session):
    runs = (
        db.query(Run)
        .order_by(Run.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": run.id,
            "tracker_id": run.tracker_id,
            "status": run.status,
            "started_at": run.started_at,
            "ended_at": run.ended_at,
            "inserted_games": run.inserted_games,
            "matched_games": run.matched_games,
            "error_message": run.error_message,
        }
        for run in runs
    ]


def get_recent_games(limit: int, db: Session):
    games = (
        db.query(Game)
        .order_by(Game.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": game.id,
            "external_id": game.external_id,
            "title": game.title,
            "studio": game.studio,
            "region": game.region,
            "genre": game.genre,
            "platform": game.platform,
            "release_date": game.release_date,
            "latest_update_date": game.latest_update_date,
            "source": game.source,
            "created_at": game.created_at,
        }
        for game in games
    ]


def get_active_trackers(limit: int, db: Session):
    trackers = (
        db.query(Tracker)
        .filter(Tracker.is_active == True)
        .order_by(Tracker.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": tracker.id,
            "name": tracker.name,
            "source": tracker.source,
            "query_json": tracker.query_json,
            "update_frequency": tracker.update_frequency,
            "is_active": tracker.is_active,
            "created_at": tracker.created_at,
        }
        for tracker in trackers
    ]
