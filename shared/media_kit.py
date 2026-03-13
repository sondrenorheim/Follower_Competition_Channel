"""
Media kit export module.
Builds website/public/api/media_kit.json from config values and API indexes.
"""

import json
from datetime import datetime
from pathlib import Path

import config


def _load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _normalize_range(value):
    if isinstance(value, dict):
        if "min" in value and "max" in value:
            return {"min": int(value["min"]), "max": int(value["max"])}
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return {"min": int(value[0]), "max": int(value[1])}
    return None


def _compute_daily_videos(index_data, window=30):
    if not index_data:
        return None
    days = index_data.get("days_metadata") or []
    if not isinstance(days, list) or not days:
        return None
    days_sorted = sorted(days, key=lambda d: d.get("day", 0), reverse=True)
    window_days = days_sorted[:window]
    counts = [d.get("games", 0) for d in window_days if isinstance(d, dict)]
    counts = [int(c) for c in counts if isinstance(c, (int, float))]
    if not counts:
        return None
    return {"min": min(counts), "max": max(counts)}


def export_media_kit(base_dir: str = "website/public/api"):
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    index_data = _load_json(base_path / "index.json") or {}
    players_index = _load_json(base_path / "players" / "index.json") or {}

    totals = {
        "total_followers": int(index_data.get("total_followers") or 0),
        "total_players": int(players_index.get("total_players") or 0),
        "total_games": int(index_data.get("total_games") or 0),
        "total_days": int(index_data.get("total_days") or 0),
        "game_modes": int(
            len(index_data.get("types_metadata") or index_data.get("game_types") or [])
        ),
    }

    override_range = _normalize_range(getattr(config, "MEDIA_KIT_DAILY_VIDEOS_RANGE", None))
    computed_range = _compute_daily_videos(index_data)
    fallback_range = _normalize_range(getattr(config, "MEDIA_KIT_DAILY_VIDEOS_FALLBACK", (6, 10)))

    daily_videos = override_range or computed_range or fallback_range or {"min": 0, "max": 0}

    output = {
        "last_updated": index_data.get("last_updated") or datetime.now().isoformat(),
        "totals": totals,
        "daily_videos": daily_videos,
        "engagement_growth_pct": getattr(config, "MEDIA_KIT_ENGAGEMENT_GROWTH_PCT", 0),
        "reach": getattr(config, "MEDIA_KIT_REACH", {}),
        "insights": getattr(config, "MEDIA_KIT_INSIGHTS", {}),
        "demographics": getattr(config, "MEDIA_KIT_DEMOGRAPHICS", {}),
        "audience_interests": getattr(config, "MEDIA_KIT_AUDIENCE_INTERESTS", []),
    }

    output_file = base_path / "media_kit.json"
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, separators=(",", ":"))

    print(f"   + Regenerated media kit stats -> {output_file}")
