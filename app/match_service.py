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