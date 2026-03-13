#!/usr/bin/env python3
"""
Rebuild website/public/api/player_history/index.json from partitioned game files.
"""

from __future__ import annotations

import json
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
    game_meta = [
        [g.get("game_id"), g.get("game_type"), g.get("day_number"), g.get("timestamp")]
        for g in games_sorted
    ]

    index_payload = {
        "lu": datetime.now().isoformat(),
        "points_scale": 10,
        "game_count": len(game_meta),
        "games": game_meta,
    }

    with (player_history_dir / "index.json").open("w", encoding="utf-8") as f:
        json.dump(index_payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Rebuilt player_history index with {len(game_meta)} games.")


if __name__ == "__main__":
    main()
