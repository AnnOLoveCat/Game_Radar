import httpx, os
from dotenv import load_dotenv
from app.error_service import (
    raise_external_service_config_error,
    raise_external_service_request_error,
    raise_unsupported_source,
)

# 加載 .env 文件中的 TOKEN
load_dotenv()
RAWG_API_KEY = os.getenv("RAWG_API_KEY")

def fetch_mock_games():
    # 不讓tracker_service直接依賴MOCK_GAMES，而是統一fetch_service取得資料。
    from app.mock_data import MOCK_GAMES
    return MOCK_GAMES


def fetch_rawg_games(query: dict | None = None):

    if not RAWG_API_KEY:
        raise_external_service_config_error("RAWG_API_KEY")
    
    # RAWG API 
    url = "https://api.rawg.io/api/games"

    params = {
        "key": RAWG_API_KEY,
        "page_size": 10,
    }
    
    if query:
        target_game = query.get("target_game", {})
        target_title = target_game.get("title")

        games = query.get("games", [])

        if target_title:
            params["search"] = target_title
        elif games:
            params["search"] = games[0]

    try:
        response = httpx.get(url, params=params, timeout=20.0)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise_external_service_request_error("RAWG", str(e))
    
    data: dict = response.json()

    results = []
    for item in data.get("results", []):
        developers = item.get("developers", [])
        developer_name = developers[0]["name"] if developers else None

        parent_platforms = item.get("parent_platforms", [])
        platform_names = []

        for p in parent_platforms:
            platform = p.get("platform")
            if platform and platform.get("name"):
                platform_names.append(platform["name"])

        results.append(
            {
                "external_id": f"rawg-{item.get('id')}",
                "title": item.get("name"),
                "studio": developer_name,
                "region": "global",
                "genre": ", ".join([g["name"] for g in item.get("genres", [])]) or None,
                "platform": " / ".join(platform_names) if platform_names else None,
                "release_date": item.get("released"),
                "latest_update_date": None,
                "source": "rawg",
            }
        )

    return results

    
def fetch_games_by_source(source: str, query: dict | None = None):
    if source == "mock":
        return fetch_mock_games()

    if source == "rawg":
        return fetch_rawg_games(query)

    raise_unsupported_source(source)