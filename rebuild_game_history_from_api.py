#!/usr/bin/env python3
"""
Rebuild game_history.json from partitioned API game files.
Merges current local history and writes atomically.
"""

from __future__ import annotations

import json
from pathlib import Path

from shared import results_store


def load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main() -> None:
    games_dir = Path("website/public/api/games")
    if not games_dir.exists():
        raise SystemExit("website/public/api/games not found.")

    api_games = []
    for path in sorted(games_dir.glob("*.json")):
        if path.name.endswith("_top.json"):
            continue
        data = load_json(path)
        if isinstance(data, dict) and data.get("game_id"):
            api_games.append(data)

    current = load_json(Path("game_history.json")) or {"games": []}
    current_games = current.get("games", []) if isinstance(current, dict) else []
    merged_games = results_store.merge_games(api_games, current_games)

    if Path("game_history.json").exists():
        results_store.create_snapshot("rebuild_game_history_from_api_before", ["game_history.json"])

    results_store.atomic_write_json("game_history.json", {"games": merged_games})
    print(f"Rebuilt game_history.json with {len(merged_games)} games.")


if __name__ == "__main__":
    main()
