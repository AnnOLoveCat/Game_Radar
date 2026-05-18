def match_game(item, query):
    region = str(item.get("region") or "unknown").strip().lower()
    title = str(item.get("title", "")).strip().lower()
    studio = str(item.get("studio", "")).strip().lower()

    regions = [str(r).strip().lower() for r in query.get("regions", [])]
    games = [str(g).strip().lower() for g in query.get("games", [])]
    is_indie = query.get("is_indie", False)
    studios = [str(s).strip().lower() for s in query.get("studios", [])]

    # 地區條件
    if regions:
        if region not in regions:
            return False

    # 遊戲名稱條件：寬鬆比對
    if games:
        if not any(g in title or title in g for g in games):
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