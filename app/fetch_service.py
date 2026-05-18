import httpx, os
from dotenv import load_dotenv
from fastapi import HTTPException

# 加載 .env 文件中的 TOKEN
load_dotenv()
RAWG_API_KEY = os.getenv("RAWG_API_KEY")

def fetch_mock_games():
    # 不讓tracker_service直接依賴MOCK_GAMES，而是統一fetch_service取得資料。
    from app.mock_data import MOCK_GAMES
    return MOCK_GAMES


def fetch_rawg_games(query: dict | None = None):

    if not RAWG_API_KEY:
        raise HTTPException(status_code=500, detail="RAWG_API_KEY is not configured")
    
    # RAWG API 
    url = "https://api.rawg.io/api/games"

    params = {
        "key": RAWG_API_KEY,
        "page_size": 10,
    }
    
    if query:
        focus = query.get("focus")

        if focus == "game":
            games = query.get("games", [])

            if games:
                params["search"] = games[0]

    try:
        response = httpx.get(url, params=params, timeout=20.0)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"RAWG request failed: {str(e)}")
    
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
                "source": "rawg",
            }
        )

    return results

    
def fetch_games_by_source(source: str, query: dict | None = None):
    if source == "mock":
        return fetch_mock_games()

    if source == "rawg":
        return fetch_rawg_games(query)

    return []