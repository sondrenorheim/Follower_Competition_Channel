"""
Rebuild player_statistics.json from partitioned API game files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config
from shared.statistics import PlayerStatistics


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def main() -> None:
    config.TEST_MODE = False
    games_dir = Path("website/public/api/games")
    if not games_dir.exists():
        raise SystemExit("website/public/api/games not found")

    # Load existing metadata so we don't clobber highscores.
    stats = PlayerStatistics("player_statistics.json")
    existing_metadata = dict(stats.metadata)
    stats.stats = {}
    stats.metadata = {
        "last_updated": existing_metadata.get("last_updated", ""),
        "total_games_recorded": 0,
        "game_highscores": existing_metadata.get("game_highscores", {}),
    }

    non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])

    game_paths = sorted(
        [p for p in games_dir.glob("*.json") if not p.name.endswith("_top.json")],
        key=lambda p: p.name,
    )

    processed_games = 0
    for idx, path in enumerate(game_paths, start=1):
        data = load_json(path)
        if not data or not data.get("game_id"):
            continue
        if data.get("non_scoring") or data.get("game_type") in non_scoring_types:
            continue

        results = data.get("results") or []
        total_participants = data.get("total_participants") or len(results)
        game_type = data.get("game_type") or ""
        game_id = data.get("game_id") or ""

        for result in results:
            username = result.get("username")
            if not username:
                continue
            placement = result.get("placement") or result.get("rank") or 0
            points = result.get("points", 0) or 0
            survival_time = result.get("survival_time", 0) or 0
            kills = result.get("kills", 0) or 0
            damage = result.get("damage", result.get("damage_dealt", 0)) or 0

            stats.update_player_stats(
                username=username,
                placement=to_int(placement),
                points_earned=to_float(points),
                survival_time=to_float(survival_time),
                total_participants=to_int(total_participants) if total_participants else 0,
                kills=to_int(kills),
                damage_dealt=to_float(damage),
                game_type=game_type,
                game_id=game_id,
            )

        processed_games += 1
        if idx % 50 == 0:
            print(f"Processed {idx}/{len(game_paths)} game files")

    stats.metadata["total_games_recorded"] = processed_games
    stats.save_statistics()
    stats.export_partitioned_stats("website/public/api")
    stats.export_web_stats("website/public/player_statistics_web.json")

    print(f"Rebuilt player stats from {processed_games} games")


if __name__ == "__main__":
    main()
