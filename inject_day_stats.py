#!/usr/bin/env python3
"""
Inject day results into website/public/api from a list of game records.
Writes games, day summary, day aggregate, type indexes, index.json, and monthly leaderboards.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import config


def load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))


def write_game_files(base: Path, games: list[dict], preview_limit: int) -> None:
    games_dir = base / "games"
    games_dir.mkdir(parents=True, exist_ok=True)
    for game in games:
        game_id = game.get("game_id")
        if not game_id:
            continue
        save_json(games_dir / f"{game_id}.json", game)
        if preview_limit > 0:
            results = game.get("results") or []
            preview = {
                "game_id": game_id,
                "game_type": game.get("game_type"),
                "game_display_name": game.get("game_display_name"),
                "day_number": game.get("day_number"),
                "timestamp": game.get("timestamp"),
                "total_participants": game.get("total_participants"),
                "results": results[:preview_limit],
                "non_scoring": game.get("non_scoring", False),
                "is_preview": True,
                "preview_limit": preview_limit,
                "total_results": len(results),
            }
            save_json(games_dir / f"{game_id}_top.json", preview)


def write_day_files(base: Path, day_number: int, games: list[dict], preview_limit: int) -> None:
    days_dir = base / "days"
    days_dir.mkdir(parents=True, exist_ok=True)

    day_summary = {
        "day_number": day_number,
        "total_games": len(games),
        "games": [
            {
                "game_id": g.get("game_id"),
                "game_type": g.get("game_type"),
                "game_display_name": g.get("game_display_name"),
                "timestamp": g.get("timestamp"),
                "total_participants": g.get("total_participants"),
                "non_scoring": g.get("non_scoring", False),
            }
            for g in games
        ],
    }
    save_json(days_dir / f"{day_number}.json", day_summary)

    non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])
    scoring_games = [
        g for g in games
        if not g.get("non_scoring") and g.get("game_type") not in non_scoring_types
    ]

    aggregated = {}
    for game in scoring_games:
        for result in game.get("results", []) or []:
            username = result.get("username")
            if not username:
                continue
            entry = aggregated.setdefault(username, {
                "username": username,
                "points": 0,
                "kills": 0,
                "survival_time": 0,
                "appearances": 0,
            })
            entry["points"] += result.get("points", 0) or 0
            entry["kills"] += result.get("kills", 0) or 0
            entry["survival_time"] += result.get("survival_time", 0) or 0
            entry["appearances"] += 1

    aggregated_results = sorted(
        aggregated.values(),
        key=lambda x: x.get("points", 0),
        reverse=True,
    )
    total_participants = len(aggregated_results)
    timestamp = max(
        (g.get("timestamp") for g in scoring_games if g.get("timestamp")),
        default=None,
    )

    aggregate_game = {
        "game_id": f"all_day_{day_number}",
        "game_type": "all",
        "game_display_name": "All Games",
        "day_number": day_number,
        "timestamp": timestamp,
        "total_participants": total_participants,
        "results": aggregated_results,
    }
    save_json(days_dir / f"{day_number}_aggregate.json", aggregate_game)
    if preview_limit > 0:
        aggregate_preview = {
            "game_id": aggregate_game["game_id"],
            "game_type": aggregate_game["game_type"],
            "game_display_name": aggregate_game["game_display_name"],
            "day_number": aggregate_game["day_number"],
            "timestamp": aggregate_game["timestamp"],
            "total_participants": total_participants,
            "results": aggregated_results[:preview_limit],
            "is_preview": True,
            "preview_limit": preview_limit,
            "total_results": total_participants,
        }
        save_json(days_dir / f"{day_number}_aggregate_top.json", aggregate_preview)


def update_type_indexes(base: Path, games: list[dict]) -> list[str]:
    types_dir = base / "types"
    types_dir.mkdir(parents=True, exist_ok=True)
    game_types = set()

    for game in games:
        game_type = game.get("game_type")
        if not game_type:
            continue
        game_types.add(game_type)
        type_file = types_dir / f"{game_type}.json"
        payload = load_json(type_file) or {"game_type": game_type, "total_games": 0, "games": []}
        existing_ids = {g.get("game_id") for g in payload.get("games", [])}
        if game.get("game_id") not in existing_ids:
            payload["games"].append({
                "game_id": game.get("game_id"),
                "day_number": game.get("day_number"),
                "timestamp": game.get("timestamp"),
                "total_participants": game.get("total_participants"),
            })
        payload["games"] = sorted(payload["games"], key=lambda x: x.get("timestamp", ""), reverse=True)
        payload["total_games"] = len(payload["games"])
        save_json(type_file, payload)

    return sorted(game_types)


def update_monthly_leaderboards(base: Path, games: list[dict], preview_limit: int) -> list[str]:
    leaderboards_dir = base / "leaderboards"
    leaderboards_dir.mkdir(parents=True, exist_ok=True)

    non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])
    monthly_data = defaultdict(lambda: defaultdict(lambda: {
        "points": 0.0,
        "games": 0,
        "wins": 0,
        "best_placement": float("inf"),
        "total_kills": 0,
        "total_placement": 0,
    }))
    monthly_data_by_type = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        "points": 0.0,
        "games": 0,
        "wins": 0,
        "best_placement": float("inf"),
        "total_kills": 0,
        "total_placement": 0,
    })))

    months = set()
    for game in games:
        if game.get("non_scoring") or game.get("game_type") in non_scoring_types:
            continue
        timestamp = game.get("timestamp", "")
        if not timestamp or len(timestamp) < 7:
            continue
        month_key = timestamp[:7]
        months.add(month_key)
        game_type = game.get("game_type") or ""
        for result in game.get("results", []) or []:
            username = result.get("username")
            if not username:
                continue
            placement = result.get("placement", 9999)
            points = result.get("points", 0) or 0
            kills = result.get("kills", 0) or 0

            player = monthly_data[month_key][username]
            player["points"] += points
            player["games"] += 1
            if placement == 1:
                player["wins"] += 1
            if placement < player["best_placement"]:
                player["best_placement"] = placement
            player["total_kills"] += kills
            player["total_placement"] += placement

            if game_type:
                typed = monthly_data_by_type[month_key][game_type][username]
                typed["points"] += points
                typed["games"] += 1
                if placement == 1:
                    typed["wins"] += 1
                if placement < typed["best_placement"]:
                    typed["best_placement"] = placement
                typed["total_kills"] += kills
                typed["total_placement"] += placement

    def build_leaderboard(players: dict) -> list[dict]:
        leaderboard = []
        for username, stats in players.items():
            leaderboard.append({
                "u": username,
                "p": round(stats["points"], 1),
                "g": stats["games"],
                "w": stats["wins"],
                "b": stats["best_placement"] if stats["best_placement"] != float("inf") else 0,
                "k": stats["total_kills"],
                "t": stats["total_placement"],
            })
        leaderboard.sort(key=lambda x: x["p"], reverse=True)
        for i, entry in enumerate(leaderboard):
            entry["r"] = i + 1
        return leaderboard

    for month in sorted(months):
        leaderboard = build_leaderboard(monthly_data[month])
        payload = {
            "month": month,
            "game_type": "all",
            "total_players": len(leaderboard),
            "leaderboard": leaderboard,
        }
        save_json(leaderboards_dir / f"{month}.json", payload)
        if preview_limit > 0 and len(leaderboard) > preview_limit:
            preview = dict(payload)
            preview["is_preview"] = True
            preview["preview_limit"] = preview_limit
            preview["total_results"] = len(leaderboard)
            preview["leaderboard"] = leaderboard[:preview_limit]
            save_json(leaderboards_dir / f"{month}_top.json", preview)

        for game_type, players in monthly_data_by_type[month].items():
            typed = build_leaderboard(players)
            payload = {
                "month": month,
                "game_type": game_type,
                "total_players": len(typed),
                "leaderboard": typed,
            }
            save_json(leaderboards_dir / f"{month}_{game_type}.json", payload)
            if preview_limit > 0 and len(typed) > preview_limit:
                preview = dict(payload)
                preview["is_preview"] = True
                preview["preview_limit"] = preview_limit
                preview["total_results"] = len(typed)
                preview["leaderboard"] = typed[:preview_limit]
                save_json(leaderboards_dir / f"{month}_{game_type}_top.json", preview)

    return sorted(months)


def update_index(base: Path, day_number: int, games: list[dict], types: list[str], months: list[str]) -> None:
    index_file = base / "index.json"
    index = load_json(index_file) or {}

    available_days = set(index.get("available_days", []) or [])
    available_days.add(day_number)

    day_types = sorted({g.get("game_type") for g in games if g.get("game_type")})
    participants = len({r.get("username") for g in games for r in (g.get("results") or []) if r.get("username")})
    day_meta = {
        "day": day_number,
        "games": len(games),
        "types": day_types,
        "participants": participants,
    }

    days_metadata = [d for d in (index.get("days_metadata") or []) if d.get("day") != day_number]
    days_metadata.append(day_meta)
    days_metadata = sorted(days_metadata, key=lambda d: d.get("day", 0))

    game_types = sorted(set(index.get("game_types", []) or []).union(types))
    types_metadata = []
    for game_type in game_types:
        type_file = base / "types" / f"{game_type}.json"
        payload = load_json(type_file) or {}
        types_metadata.append({
            "type": game_type,
            "games": payload.get("total_games", 0),
        })

    available_months = sorted(set(index.get("available_months", []) or []).union(months))
    preview_limit = int(getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)

    index.update({
        "last_updated": datetime.now().isoformat(),
        "total_games": sum(t.get("games", 0) for t in types_metadata) or index.get("total_games", 0),
        "total_days": len(available_days),
        "results_preview_limit": preview_limit,
        "available_days": sorted(available_days),
        "days_metadata": days_metadata,
        "game_types": game_types,
        "types_metadata": types_metadata,
        "available_months": available_months,
    })

    save_json(index_file, index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=int, required=True)
    parser.add_argument("--games", required=True, help="JSON list of game objects for the day")
    args = parser.parse_args()

    base = Path("website/public/api")
    preview_limit = int(getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)

    with Path(args.games).open("r", encoding="utf-8") as f:
        games = json.load(f)

    write_game_files(base, games, preview_limit)
    write_day_files(base, args.day, games, preview_limit)
    types = update_type_indexes(base, games)
    months = update_monthly_leaderboards(base, games, preview_limit)
    update_index(base, args.day, games, types, months)

    print(f"Injected day {args.day} stats into website/public/api.")


if __name__ == "__main__":
    main()
