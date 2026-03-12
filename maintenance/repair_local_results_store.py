#!/usr/bin/env python3
"""
One-time repair/migration for local game result storage.

Merges all available history sources into a canonical game_history.json,
rebuilds player_statistics.json, and writes a migration report.
"""

from __future__ import annotations

import argparse
import json
import mmap
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config
from shared import results_store
from shared.statistics import PlayerStatistics


def _iter_game_objects(mm: mmap.mmap, start: int):
    in_string = False
    escape = False
    depth = 0
    collecting = False
    buffer = bytearray()

    for index in range(start, len(mm)):
        char = mm[index]

        if not collecting:
            if char == ord("{"):
                collecting = True
                depth = 1
                in_string = False
                escape = False
                buffer = bytearray()
                buffer.append(char)
            elif char == ord("]"):
                break
            continue

        buffer.append(char)

        if in_string:
            if escape:
                escape = False
            elif char == ord("\\"):
                escape = True
            elif char == ord('"'):
                in_string = False
            continue

        if char == ord('"'):
            in_string = True
        elif char == ord("{"):
            depth += 1
        elif char == ord("}"):
            depth -= 1
            if depth == 0:
                yield bytes(buffer)
                collecting = False
                buffer = bytearray()


def _iter_games_from_history_file(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and isinstance(payload.get("games"), list):
            for game in payload.get("games", []):
                if isinstance(game, dict):
                    yield game
            return
    except Exception:
        pass

    # Fallback parser for very large/partially malformed files.
    try:
        with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            marker = b"\"games\":["
            marker_pos = mm.find(marker)
            if marker_pos == -1:
                return
            array_start = marker_pos + len(marker)
            for raw in _iter_game_objects(mm, array_start):
                try:
                    game = json.loads(raw.decode("utf-8"))
                except Exception:
                    continue
                if isinstance(game, dict):
                    yield game
    except Exception:
        return


def _collect_api_games(games_dir: Path):
    for path in sorted(games_dir.glob("*.json")):
        if path.name.endswith("_top.json"):
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                yield payload
        except Exception:
            continue


def _merge_source(
    source_name: str,
    games: Iterable[dict[str, Any]],
    merged_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    seen = 0
    merged = 0
    skipped = 0
    for game in games:
        if not isinstance(game, dict):
            skipped += 1
            continue
        game_id = game.get("game_id")
        if not isinstance(game_id, str) or not game_id:
            skipped += 1
            continue
        seen += 1
        existing = merged_by_id.get(game_id)
        preferred = results_store.choose_preferred_game(existing or {}, game)
        if existing is None or preferred is not existing:
            merged += 1
        merged_by_id[game_id] = preferred

    return {
        "source": source_name,
        "games_seen": seen,
        "games_merged": merged,
        "games_skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair local game/stats storage from all available sources.")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and report without writing files.")
    args = parser.parse_args()

    repo_root = REPO_ROOT
    config.TEST_MODE = False

    merged_by_id: dict[str, dict[str, Any]] = {}
    source_reports: list[dict[str, Any]] = []

    api_games_dir = repo_root / "website" / "public" / "api" / "games"
    if api_games_dir.exists():
        source_reports.append(_merge_source("api_games", _collect_api_games(api_games_dir), merged_by_id))
    else:
        source_reports.append({"source": "api_games", "games_seen": 0, "games_merged": 0, "games_skipped": 0, "missing": True})

    history_path = repo_root / "game_history.json"
    if history_path.exists():
        source_reports.append(_merge_source("game_history.json", _iter_games_from_history_file(history_path), merged_by_id))
    else:
        source_reports.append({"source": "game_history.json", "games_seen": 0, "games_merged": 0, "games_skipped": 0, "missing": True})

    recovered_path = repo_root / "game_history_recovered.json"
    if recovered_path.exists():
        source_reports.append(_merge_source("game_history_recovered.json", _iter_games_from_history_file(recovered_path), merged_by_id))
    else:
        source_reports.append({"source": "game_history_recovered.json", "games_seen": 0, "games_merged": 0, "games_skipped": 0, "missing": True})

    backup_files = sorted(repo_root.glob("game_history_backup_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if backup_files:
        for backup_file in backup_files:
            report_name = backup_file.name
            source_reports.append(_merge_source(report_name, _iter_games_from_history_file(backup_file), merged_by_id))
    else:
        source_reports.append({"source": "game_history_backup_*.json", "games_seen": 0, "games_merged": 0, "games_skipped": 0, "missing": True})

    canonical_games = sorted(
        merged_by_id.values(),
        key=lambda g: (str(g.get("timestamp", "")), str(g.get("game_id", ""))),
    )
    canonical_payload = {"games": canonical_games}

    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": bool(args.dry_run),
        "total_unique_games": len(canonical_games),
        "sources": source_reports,
        "actions": [],
    }

    if not args.dry_run:
        results_store.create_snapshot("migration_repair_before", ["game_history.json", "player_statistics.json"])
        results_store.atomic_write_json("game_history.json", canonical_payload)
        report["actions"].append("wrote game_history.json")

        stats = PlayerStatistics.rebuild_from_games(
            canonical_games,
            stats_file="player_statistics.json",
        )
        report["actions"].append(
            f"rebuilt player_statistics.json ({len(stats.stats)} players, {stats.metadata.get('total_games_recorded', 0)} games)"
        )

        snapshot_dir = results_store.create_snapshot("migration_repair", ["game_history.json", "player_statistics.json"])
        report["actions"].append(f"created snapshot {snapshot_dir.name}")

    report_name = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = repo_root / "backups" / "game_results" / report_name
    results_store.atomic_write_json(report_path, report)

    print(f"Repair report written: {report_path}")
    print(f"Canonical unique games: {len(canonical_games)}")
    if args.dry_run:
        print("Dry run only. No canonical files were written.")
    else:
        print("Canonical files repaired and snapshots created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
