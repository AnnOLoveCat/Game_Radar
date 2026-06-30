def match_game(item, query):
    region = str(item.get("region") or "unknown").strip().lower()
    title = str(item.get("title", "")).strip().lower()
    studio = str(item.get("studio", "")).strip().lower()
    genre = str(item.get("genre", "")).strip().lower()
    platform = str(item.get("platform", "")).strip().lower()

    target_game = query.get("target_game", {})
    target_title = str(target_game.get("title", "")).strip().lower()

    regions = [str(r).strip().lower() for r in query.get("regions", [])]
    games = [str(g).strip().lower() for g in query.get("games", [])]
    genres = [str(g).strip().lower() for g in query.get("genres", [])]
    platforms = [str(p).strip().lower() for p in query.get("platforms", [])]

    is_indie = query.get("is_indie", False)
    studios = [str(s).strip().lower() for s in query.get("studios", [])]

    if target_title and target_title not in games:
        games.append(target_title)

    # 地區條件
    if regions:
        if region not in regions:
            return False

    # 遊戲名稱條件：寬鬆比對
    if games:
        if not any(g in title or title in g for g in games):
            return False

    # 類型條件：寬鬆比對
    if genres:
        if not any(g in genre or genre in g for g in genres):
            return False

    # 平台條件：寬鬆比對
    if platforms:
        if not any(p in platform or platform in p for p in platforms):
            return False

    # 開發商條件：寬鬆比對
    if studios:
        if not any(s in studio or studio in s for s in studios):
            return False

    # 是否為獨立遊戲
    if is_indie:
        if "indie" not in studio and "studio" not in studio:
            return False

    return True