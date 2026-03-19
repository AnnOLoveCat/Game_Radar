from sqlalchemy import inspect
from app.db import engine

insp = inspect(engine)
tables = insp.get_table_names()
print("Tables:", tables)
print("trackers exists?", "trackers" in tables)
print("games exists?", "games" in tables)
print("game_matches exists?", "game_matches" in tables)