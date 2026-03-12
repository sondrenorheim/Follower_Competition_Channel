#!/usr/bin/env python3
"""
Verify local game results store integrity.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared import results_store


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _game_count_from_payload(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    games = payload.get("games")
    if not isinstance(games, list):
        return 0
    ids = {
        game.get("game_id")
        for game in games
        if isinstance(game, dict) and isinstance(game.get("game_id"), str) and game.get("game_id")
    }
    return len(ids)


def _player_count_from_payload(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    if isinstance(payload.get("players"), dict):
        return len(payload.get("players", {}))
    metadata_keys = {"last_updated", "total_games_recorded", "game_highscores"}
    keys = [k for k in payload.keys() if k not in metadata_keys]
    return len(keys)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify game/stat storage integrity.")
    parser.add_argument("--strict", action="store_true", help="Escalate recoverable mismatches to critical.")
    args = parser.parse_args()

    repo_root = REPO_ROOT
    critical: list[str] = []
    recoverable: list[str] = []
    notices: list[str] = []

    history_path = repo_root / "game_history.json"
    stats_path = repo_root / "player_statistics.json"

    history_payload, history_source = results_store.load_best_game_history("game_history.json")
    if not isinstance(history_payload, dict) or not isinstance(history_payload.get("games"), list):
        critical.append("No valid game history source could be loaded")
        monolith_games = 0
    else:
        monolith_games = _game_count_from_payload(history_payload)
        notices.append(f"Monolith game count: {monolith_games}")
        if history_source and Path(history_source).resolve() != history_path.resolve():
            recoverable.append(
                f"Primary game_history.json was not selected as best source (using {history_source})"
            )

    stats_payload, stats_source = results_store.load_best_player_stats("player_statistics.json")
    if not isinstance(stats_payload, dict):
        critical.append("No valid player statistics source could be loaded")
        stats_players = 0
    else:
        stats_players = _player_count_from_payload(stats_payload)
        notices.append(f"Player stats count: {stats_players}")
        if stats_source and Path(stats_source).resolve() != stats_path.resolve():
            recoverable.append(
                f"Primary player_statistics.json was not selected as best source (using {stats_source})"
            )

    api_games_count = results_store.count_api_games()
    notices.append(f"API partition game files: {api_games_count}")

    event_payload = results_store.load_games_from_events()
    event_games_count = _game_count_from_payload(event_payload)
    notices.append(f"Event log unique games: {event_games_count}")

    if monolith_games and api_games_count and monolith_games < api_games_count:
        recoverable.append(
            f"Monolith game count ({monolith_games}) is lower than API partitions ({api_games_count})"
        )
    if monolith_games and event_games_count and monolith_games < event_games_count:
        recoverable.append(
            f"Monolith game count ({monolith_games}) is lower than event logs ({event_games_count})"
        )

    snapshots_root = repo_root / "backups" / "game_results" / "snapshots"
    snapshot_count = 0
    checksum_failures = 0
    if snapshots_root.exists():
        for snapshot_dir in sorted(snapshots_root.iterdir()):
            if not snapshot_dir.is_dir():
                continue
            metadata_path = snapshot_dir / "metadata.json"
            metadata = _load_json(metadata_path)
            if not isinstance(metadata, dict):
                recoverable.append(f"Snapshot metadata missing/invalid: {metadata_path}")
                continue
            snapshot_count += 1
            for item in metadata.get("files", []):
                if not isinstance(item, dict):
                    continue
                if not item.get("exists"):
                    continue
                snapshot_file = item.get("snapshot_file")
                expected_sha = item.get("sha256")
                if not isinstance(snapshot_file, str) or not snapshot_file:
                    continue
                candidate = snapshot_dir / snapshot_file
                if not candidate.exists():
                    checksum_failures += 1
                    recoverable.append(f"Snapshot file missing: {candidate}")
                    continue
                if isinstance(expected_sha, str) and expected_sha:
                    try:
                        actual_sha = results_store.sha256_file(candidate)
                    except Exception as exc:
                        checksum_failures += 1
                        recoverable.append(f"Checksum read failed for {candidate}: {exc}")
                        continue
                    if actual_sha != expected_sha:
                        checksum_failures += 1
                        recoverable.append(f"Checksum mismatch: {candidate}")
    notices.append(f"Snapshots checked: {snapshot_count}")
    if checksum_failures:
        notices.append(f"Snapshot checksum failures: {checksum_failures}")

    verify_state_path = repo_root / "backups" / "game_results" / "manifests" / "verify_state.json"
    previous_max = 0
    verify_state = _load_json(verify_state_path)
    if isinstance(verify_state, dict):
        try:
            previous_max = int(verify_state.get("max_monolith_games", 0) or 0)
        except Exception:
            previous_max = 0

    if previous_max > 0 and monolith_games > 0 and monolith_games < previous_max:
        recoverable.append(
            f"Monotonicity warning: game count dropped from {previous_max} to {monolith_games}"
        )

    if monolith_games > previous_max:
        state_payload = {
            "updated_at": datetime.now().isoformat(),
            "max_monolith_games": monolith_games,
        }
        results_store.atomic_write_json(verify_state_path, state_payload)

    if critical:
        status = 2
    elif recoverable:
        status = 2 if args.strict else 1
    else:
        status = 0

    print("Verification summary")
    for line in notices:
        print(f"  - {line}")
    if recoverable:
        print("Recoverable findings")
        for issue in recoverable:
            print(f"  - {issue}")
    if critical:
        print("Critical findings")
        for issue in critical:
            print(f"  - {issue}")

    if status == 0:
        print("Status: healthy")
    elif status == 1:
        print("Status: recoverable mismatch")
    else:
        print("Status: critical integrity failure")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
