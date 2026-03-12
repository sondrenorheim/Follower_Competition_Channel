#!/usr/bin/env python3
"""
Rebuild canonical history/stat files from append-only event logs.

Default behavior:
1) load games from backups/game_results/events
2) optionally merge in existing API game files as baseline
3) write game_history.json
4) rebuild player_statistics.json from merged games
5) regenerate website/public/api outputs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config
from shared import results_store
from shared.game_history import GameHistory
from shared.statistics import PlayerStatistics


def _load_api_games(base_dir: Path) -> list[dict]:
    games_dir = base_dir / "games"
    if not games_dir.exists():
        return []

    games: list[dict] = []
    for path in sorted(games_dir.glob("*.json")):
        if path.name.endswith("_top.json"):
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("game_id"):
            games.append(payload)
    return games


def _build_history_payload(include_api_baseline: bool, api_dir: Path) -> dict:
    events_payload = results_store.load_games_from_events()
    events_games = events_payload.get("games", []) if isinstance(events_payload, dict) else []
    if include_api_baseline:
        api_games = _load_api_games(api_dir)
        merged_games = results_store.merge_games(api_games, events_games)
    else:
        merged_games = results_store.merge_games(events_games)
    return {"games": merged_games}


def _export_partitioned_history(payload: dict, api_dir: Path) -> None:
    gh = GameHistory.__new__(GameHistory)
    gh.history_file = "game_history.json"
    gh.history = payload
    gh.light_mode = False
    gh._light_id_counter = 0
    gh._light_save_notice_printed = False
    gh.export_partitioned_history(str(api_dir))
    try:
        gh.export_hall_of_fame(str(api_dir))
    except Exception as exc:
        print(f"Warning: hall_of_fame export failed: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild canonical history/stat files from event logs.")
    parser.add_argument(
        "--events-only",
        action="store_true",
        help="Use only backups/game_results/events (skip API games baseline merge).",
    )
    parser.add_argument(
        "--no-export-api",
        action="store_true",
        help="Skip regenerating website/public/api outputs.",
    )
    args = parser.parse_args()

    include_api_baseline = not args.events_only
    api_dir = REPO_ROOT / "website" / "public" / "api"

    original_test_mode = bool(getattr(config, "TEST_MODE", False))
    original_light_mode = bool(getattr(config, "SIMULATION_LIGHT_MODE", False))

    try:
        config.TEST_MODE = False
        config.SIMULATION_LIGHT_MODE = False

        payload = _build_history_payload(include_api_baseline, api_dir)
        games = payload.get("games", [])
        total_games = len(games)
        if total_games == 0:
            print("No games found in event logs/API baseline. Nothing to rebuild.")
            return 1

        results_store.atomic_write_json("game_history.json", payload)
        print(f"Wrote game_history.json with {total_games} merged games")

        stats = PlayerStatistics.rebuild_from_games(
            games,
            stats_file="player_statistics.json",
            preserve_highscores=True,
        )
        print(
            "Rebuilt player_statistics.json: "
            f"{len(stats.stats)} players, {stats.metadata.get('total_games_recorded', 0)} games"
        )

        if not args.no_export_api:
            _export_partitioned_history(payload, api_dir)
            stats.export_partitioned_stats(str(api_dir))
            stats.export_web_stats("website/public/player_statistics_web.json")
            print("Regenerated website/public/api and player_statistics_web.json")

        print("Rebuild complete.")
        return 0
    finally:
        config.TEST_MODE = original_test_mode
        config.SIMULATION_LIGHT_MODE = original_light_mode


if __name__ == "__main__":
    raise SystemExit(main())
