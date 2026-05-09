#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config
from shared import cloud_sync, media_kit, results_store
from shared.game_history import GameHistory
from shared.platform_targets import is_noncanonical_record_game_type
from shared.statistics import PlayerStatistics
from shared.website_delta_sync import WebsiteDeltaSync


def _run_club_member_stats() -> None:
    script = REPO_ROOT / "build_club_member_stats.py"
    if not script.exists():
        return
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"build_club_member_stats.py failed: {stderr or completed.returncode}")


def _load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _current_api_max_day(api_dir: Path) -> int:
    candidates: list[int] = []

    hall_of_fame = _load_json(api_dir / "hall_of_fame.json", {})
    for entry in list(hall_of_fame.get("daily_champions") or []):
        try:
            candidates.append(int(entry.get("day") or 0))
        except Exception:
            continue

    history_index = _load_json(api_dir / "player_history" / "index.json", {})
    for meta in list(history_index.get("games") or []):
        if not isinstance(meta, list) or len(meta) < 3:
            continue
        try:
            candidates.append(int(meta[2] or 0))
        except Exception:
            continue

    index_payload = _load_json(api_dir / "index.json", {})
    for value in list(index_payload.get("available_days") or []):
        try:
            candidates.append(int(value or 0))
        except Exception:
            continue
    for entry in list(index_payload.get("days_metadata") or []):
        try:
            candidates.append(int((entry or {}).get("day") or 0))
        except Exception:
            continue

    valid = [value for value in candidates if value > 0]
    return max(valid) if valid else 0


def _iter_games_from_history_stream(history_path: Path) -> Any:
    in_games_array = False
    capturing = False
    in_string = False
    escape = False
    brace_depth = 0
    current_chars: list[str] = []

    with history_path.open("r", encoding="utf-8") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            for char in chunk:
                if not in_games_array:
                    if char == "[":
                        in_games_array = True
                    continue

                if not capturing:
                    if char == "{":
                        capturing = True
                        brace_depth = 1
                        in_string = False
                        escape = False
                        current_chars = ["{"]
                    elif char == "]":
                        return
                    continue

                current_chars.append(char)
                if escape:
                    escape = False
                    continue
                if char == "\\" and in_string:
                    escape = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == "{":
                    brace_depth += 1
                    continue
                if char == "}":
                    brace_depth -= 1
                    if brace_depth == 0:
                        yield json.loads("".join(current_chars))
                        capturing = False
                        current_chars = []

    if capturing:
        raise RuntimeError(f"Incomplete game object while streaming {history_path}")


def _iter_history_day_batches(
    history_path: Path,
    *,
    from_day: int,
    to_day: int | None,
) -> Any:
    current_day: int | None = None
    current_payloads: list[dict[str, Any]] = []
    for payload in _iter_games_from_history_stream(history_path):
        if not isinstance(payload, dict):
            continue
        game_id = str(payload.get("game_id") or "").strip()
        game_type = str(payload.get("game_type") or "").strip().lower()
        if not game_id or not game_type or is_noncanonical_record_game_type(game_type):
            continue
        try:
            day_number = int(payload.get("day_number") or 0)
        except Exception:
            day_number = 0
        if day_number <= 0 or day_number < int(from_day):
            continue
        if to_day is not None and day_number > int(to_day):
            continue
        if current_day is None:
            current_day = day_number
        if day_number != current_day:
            if day_number < current_day:
                raise RuntimeError(
                    "game_history.json is not ordered by day_number, so the low-disk bootstrap path cannot batch by day safely."
                )
            yield current_day, current_payloads
            current_day = day_number
            current_payloads = []
        current_payloads.append(payload)

    if current_day is not None and current_payloads:
        yield current_day, current_payloads


def _write_day_event_cache(day_number: int, payloads: list[dict[str, Any]], events_root: Path) -> int:
    games_dir = events_root / "games"
    days_dir = events_root / "days"
    games_dir.mkdir(parents=True, exist_ok=True)
    days_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    game_count = 0
    for payload in payloads:
        game_id = str(payload.get("game_id") or "").strip()
        game_type = str(payload.get("game_type") or "").strip().lower()
        if not game_id or not game_type or is_noncanonical_record_game_type(game_type):
            continue
        results_store.atomic_write_json(games_dir / f"{game_id}.json", payload)
        entries.append(
            {
                "game_id": game_id,
                "game_type": game_type,
                "game_display_name": payload.get("game_display_name"),
                "timestamp": str(payload.get("timestamp") or ""),
                "total_participants": int(payload.get("total_participants") or len(payload.get("results") or [])),
                "day_number": int(day_number),
                "non_scoring": bool(payload.get("non_scoring", False)),
            }
        )
        game_count += 1

    entries.sort(key=lambda item: (str(item.get("timestamp") or ""), str(item.get("game_id") or "")))
    results_store.atomic_write_json(
        days_dir / f"{int(day_number)}.json",
        {
            "day_number": int(day_number),
            "games": entries,
        },
    )
    return game_count


def _run_incremental_catchup(
    *,
    api_dir: Path,
    from_day: int,
    to_day: int | None,
    publish: bool,
) -> int:
    history_path = REPO_ROOT / "game_history.json"
    if not history_path.exists():
        raise RuntimeError(f"Missing historical game source: {history_path}")

    all_changed_paths: set[str] = set()
    synced_days = 0
    synced_games = 0
    first_day: int | None = None
    last_day: int | None = None

    for day_number, payloads in _iter_history_day_batches(
        history_path,
        from_day=from_day,
        to_day=to_day,
    ):
        with tempfile.TemporaryDirectory(prefix=f"fbg-website-day-{int(day_number)}-") as tmp_dir:
            events_root = Path(tmp_dir) / "events"
            day_game_count = _write_day_event_cache(int(day_number), payloads, events_root)
            if day_game_count <= 0:
                continue
            if first_day is None:
                first_day = int(day_number)
            last_day = int(day_number)
            print(f"Syncing website day delta for Day {day_number} ({day_game_count} historical games)...")
            syncer = WebsiteDeltaSync(
                repo_root=REPO_ROOT,
                public_dir=api_dir.parent,
                api_dir=api_dir,
                events_days_dir=events_root / "days",
                events_games_dir=events_root / "games",
            )
            result = syncer.sync_day(
                int(day_number),
                publish_to_r2=False,
                refresh_club_member_stats=False,
            )
            if not result.ok:
                raise RuntimeError(
                    f"Website delta catch-up failed for Day {day_number}: {result.output_excerpt or result.publish_message}"
                )
            synced_days += 1
            synced_games += int(day_game_count)
            all_changed_paths.update(result.changed_api_paths)
            print(
                f"   Day {day_number} OK: {result.changed_count} changed API file(s), "
                f"{len(result.new_game_ids)} new game(s)"
            )

    if synced_days <= 0:
        print(f"No historical website catch-up needed from Day {from_day}.")
        return 0

    _run_club_member_stats()
    all_changed_paths.add("club_members_stats.json")

    if publish and bool(getattr(config, "AUTO_PUSH_SYNC_R2_FROM_LOCAL", False)) and all_changed_paths:
        publish_result = cloud_sync.push_api_files(sorted(all_changed_paths), api_dir=api_dir)
        print(publish_result.message)
        if not publish_result.ok:
            return 1

    print(
        "Incremental website catch-up complete. "
        f"Updated {synced_days} day(s), {synced_games} historical game(s), and {len(all_changed_paths)} API file(s) "
        f"(Day {first_day} -> Day {last_day})."
    )
    return 0


def _run_full_rebuild(*, api_dir: Path, publish: bool) -> int:
    original_test_mode = bool(getattr(config, "TEST_MODE", False))
    original_light_mode = bool(getattr(config, "SIMULATION_LIGHT_MODE", False))

    try:
        config.TEST_MODE = False
        config.SIMULATION_LIGHT_MODE = False

        payload, source = results_store.load_best_game_history("game_history.json")
        games = list(payload.get("games") or []) if isinstance(payload, dict) else []
        if not games:
            raise RuntimeError("No historical games found for website bootstrap.")

        gh = GameHistory.__new__(GameHistory)
        gh.history_file = "game_history.json"
        gh.history = {"games": games}
        gh.light_mode = False
        gh._light_id_counter = 0
        gh._light_save_notice_printed = False

        print(f"Bootstrapping website API from {source or 'unknown source'} with {len(games)} game(s).")
        gh.export_partitioned_history(str(api_dir))
        gh.export_hall_of_fame(str(api_dir))

        stats = PlayerStatistics.rebuild_from_games(
            games,
            stats_file="player_statistics.json",
            preserve_highscores=True,
        )
        stats.export_partitioned_stats(str(api_dir))
        media_kit.export_media_kit(str(api_dir))
        _run_club_member_stats()

        if publish and bool(getattr(config, "AUTO_PUSH_SYNC_R2_FROM_LOCAL", False)):
            result = cloud_sync.push_api_snapshot(api_dir)
            print(result.message)
            if not result.ok:
                return 1

        print("Website API full baseline bootstrap complete.")
        return 0
    finally:
        config.TEST_MODE = original_test_mode
        config.SIMULATION_LIGHT_MODE = original_light_mode


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the website API baseline from the best historical source.")
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Rebuild local website/public/api only; skip the final R2 publish.",
    )
    parser.add_argument(
        "--from-day",
        type=int,
        default=None,
        help="Override the starting day for the incremental catch-up path.",
    )
    parser.add_argument(
        "--to-day",
        type=int,
        default=None,
        help="Optional upper bound day for the incremental catch-up path.",
    )
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Force the original full in-memory bootstrap instead of the safer delta catch-up path.",
    )
    args = parser.parse_args()

    api_dir = REPO_ROOT / "website" / "public" / "api"
    publish = not bool(args.no_publish)

    if args.full_rebuild:
        return _run_full_rebuild(api_dir=api_dir, publish=publish)

    current_max_day = _current_api_max_day(api_dir)
    from_day = int(args.from_day) if args.from_day is not None else max(1, current_max_day + 1)
    print(
        f"Current website baseline reaches Day {current_max_day}. "
        f"Starting incremental catch-up from Day {from_day}."
    )
    return _run_incremental_catchup(
        api_dir=api_dir,
        from_day=from_day,
        to_day=args.to_day,
        publish=publish,
    )


if __name__ == "__main__":
    raise SystemExit(main())
