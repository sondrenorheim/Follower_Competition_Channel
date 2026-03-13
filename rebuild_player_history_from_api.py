#!/usr/bin/env python3
"""
Rebuild website/public/api/player_history from partitioned game files.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main() -> None:
    base_dir = Path("website/public/api")
    games_dir = base_dir / "games"
    player_history_dir = base_dir / "player_history"
    player_history_dir.mkdir(parents=True, exist_ok=True)

    games = []
    for path in games_dir.glob("*.json"):
        if path.name.endswith("_top.json"):
            continue
        data = load_json(path)
        if data and data.get("game_id"):
            games.append(data)

    games_sorted = sorted(games, key=lambda g: g.get("timestamp", ""), reverse=True)

    game_meta = []
    player_histories = defaultdict(lambda: defaultdict(list))
    points_scale = 10

    for game in games_sorted:
        game_id = game.get("game_id")
        if not game_id:
            continue
        game_index = len(game_meta)
        game_meta.append([
            game_id,
            game.get("game_type"),
            game.get("day_number"),
            game.get("timestamp"),
        ])

        for result in game.get("results", []) or []:
            username = result.get("username")
            if not username:
                continue
            first_char = username[0].lower()
            letter = first_char if first_char.isalpha() else "0"
            placement = result.get("placement", 0) or 0
            points = result.get("points", 0) or 0
            kills = result.get("kills", 0) or 0
            points_scaled = int(round(points * points_scale))
            player_histories[letter][username].append([
                game_index,
                placement,
                points_scaled,
                kills,
            ])

    for letter in sorted(player_histories.keys()):
        players = player_histories[letter]
        payload = {
            "letter": letter,
            "count": len(players),
            "players": players,
        }
        with (player_history_dir / f"{letter}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    index_payload = {
        "lu": datetime.now().isoformat(),
        "points_scale": points_scale,
        "game_count": len(game_meta),
        "games": game_meta,
    }
    with (player_history_dir / "index.json").open("w", encoding="utf-8") as f:
        json.dump(index_payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Rebuilt player_history with {len(game_meta)} games.")


if __name__ == "__main__":
    main()
