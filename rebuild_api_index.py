#!/usr/bin/env python3
"""
Rebuild website/public/api/index.json from existing partitioned API files.
Uses api/days, api/types, and api/leaderboards to populate metadata.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import config


def load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main() -> None:
    base_dir = Path("website/public/api")
    days_dir = base_dir / "days"
    types_dir = base_dir / "types"
    leaderboards_dir = base_dir / "leaderboards"

    day_files = sorted(p for p in days_dir.glob("*.json") if "_aggregate" not in p.name)
    days_metadata = []
    available_days = []
    total_games = 0

    for path in day_files:
        payload = load_json(path)
        if not payload:
            continue
        day_num = payload.get("day_number")
        if day_num is None:
            continue
        available_days.append(day_num)
        games = payload.get("games", []) or []
        total_games += len(games)
        game_types = sorted({g.get("game_type") for g in games if g.get("game_type")})
        participants = len({r.get("username") for g in games for r in (g.get("results") or []) if r.get("username")})
        days_metadata.append({
            "day": day_num,
            "games": len(games),
            "types": game_types,
            "participants": participants,
        })

    type_files = sorted(p for p in types_dir.glob("*.json"))
    game_types = []
    types_metadata = []
    for path in type_files:
        payload = load_json(path)
        if not payload:
            continue
        game_type = payload.get("game_type")
        if not game_type:
            continue
        game_types.append(game_type)
        types_metadata.append({
            "type": game_type,
            "games": payload.get("total_games", 0),
        })

    month_files = [p for p in leaderboards_dir.glob("*.json") if "_top" not in p.name and "_" not in p.stem]
    available_months = sorted(p.stem for p in month_files)

    total_followers = 0
    try:
        followers_file = Path(config.FOLLOWER_IMPORT_FILE)
        if followers_file.exists():
            with followers_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                total_followers = len(data)
            elif isinstance(data, dict) and "followers" in data:
                total_followers = len(data["followers"])
    except Exception:
        pass

    preview_limit = int(getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)

    index_data = {
        "last_updated": datetime.now().isoformat(),
        "total_games": total_games,
        "total_days": len(available_days),
        "total_followers": total_followers,
        "results_preview_limit": preview_limit,
        "available_days": sorted(set(available_days)),
        "days_metadata": sorted(days_metadata, key=lambda d: d["day"]),
        "game_types": sorted(set(game_types)),
        "types_metadata": types_metadata,
        "available_months": available_months,
    }

    base_dir.mkdir(parents=True, exist_ok=True)
    with (base_dir / "index.json").open("w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Rebuilt index.json with {len(index_data['available_days'])} days.")


if __name__ == "__main__":
    main()
