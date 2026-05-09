from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import config
from . import results_store
from .platform_targets import is_noncanonical_record_game_type


WEBSITE_PLATFORMS: tuple[str, ...] = ("instagram", "youtube", "facebook")
PLATFORM_LABELS: dict[str, str] = {
    "instagram": "Instagram",
    "youtube": "YouTube",
    "facebook": "Facebook",
}
DEFAULT_POINTS_SCALE = 10
PLAYER_STATS_FIELDS = 13


@dataclass(frozen=True)
class WebsitePlatformGame:
    platform: str
    game: dict[str, Any]


def normalize_website_platform(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in WEBSITE_PLATFORMS:
        return normalized
    return "instagram"


def normalize_website_game_type(game_type: str | None) -> str:
    normalized = str(game_type or "").strip().lower()
    for prefix in ("youtube_followers_", "facebook_", "youtube_"):
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized


def normalize_website_game_display_name(game_type: str | None, display_name: str | None = None) -> str:
    text = str(display_name or "").strip()
    if text:
        text = re.sub(r"\s*\((?:youtube followers|youtube|facebook)\)\s*$", "", text, flags=re.IGNORECASE).strip()
    if text:
        return text
    base_type = normalize_website_game_type(game_type)
    overrides = {
        "follower_pacman": "Follower Pac-Man",
    }
    return overrides.get(base_type, base_type.replace("_", " ").title() if base_type else "Follower Battlegrounds")


def _repo_path(path_value: str | Path | None, repo_root: Path) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = repo_root / path
    return path


def _load_mapping_keys(path: Path | None) -> set[tuple[int, str]]:
    if path is None or not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if not isinstance(payload, dict):
        return set()
    keys: set[tuple[int, str]] = set()
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        try:
            day_number = int(entry.get("day_number") or 0)
        except Exception:
            day_number = 0
        game_type = str(entry.get("game_type") or "").strip().lower()
        if day_number > 0 and game_type:
            keys.add((day_number, game_type))
    return keys


def load_platform_post_keys(repo_root: str | Path | None = None) -> dict[str, set[tuple[int, str]]]:
    root = Path(repo_root or getattr(config, "PROJECT_ROOT", ".")).resolve()
    youtube_path = _repo_path(getattr(config, "YOUTUBE_MEDIA_GAME_MAP_PATH", ""), root)
    facebook_path = _repo_path(getattr(config, "FACEBOOK_MEDIA_GAME_MAP_PATH", ""), root)
    return {
        "youtube": _load_mapping_keys(youtube_path),
        "facebook": _load_mapping_keys(facebook_path),
    }


def _explicit_platforms(game: dict[str, Any]) -> set[str]:
    platforms: set[str] = set()
    scalar_keys = (
        "website_platform",
        "result_platform",
        "published_platform",
        "posted_platform",
        "upload_platform",
    )
    list_keys = (
        "website_platforms",
        "result_platforms",
        "published_platforms",
        "posted_platforms",
        "upload_platforms",
    )
    for key in scalar_keys:
        value = str(game.get(key) or "").strip().lower()
        if value in WEBSITE_PLATFORMS:
            platforms.add(value)
    for key in list_keys:
        values = game.get(key)
        if isinstance(values, str):
            values = [part.strip() for part in values.split(",")]
        if not isinstance(values, (list, tuple, set)):
            continue
        for value in values:
            normalized = str(value or "").strip().lower()
            if normalized in WEBSITE_PLATFORMS:
                platforms.add(normalized)
    return platforms


def classify_game_platforms(
    game: dict[str, Any],
    post_keys: dict[str, set[tuple[int, str]]] | None = None,
) -> set[str]:
    raw_type = str(game.get("game_type") or "").strip().lower()
    try:
        day_number = int(game.get("day_number") or 0)
    except Exception:
        day_number = 0

    platforms = _explicit_platforms(game)
    lookup_key = (day_number, raw_type)
    for platform, keys in (post_keys or {}).items():
        if platform in WEBSITE_PLATFORMS and lookup_key in keys:
            platforms.add(platform)

    is_youtube_native = raw_type.startswith("youtube_") and not raw_type.startswith("youtube_followers_")
    is_audience_only = is_noncanonical_record_game_type(raw_type)

    if is_youtube_native:
        platforms.add("youtube")
    elif not is_audience_only:
        platforms.add("instagram")

    return {platform for platform in platforms if platform in WEBSITE_PLATFORMS}


def _platform_game_copy(game: dict[str, Any], platform: str) -> dict[str, Any]:
    raw_type = str(game.get("game_type") or "").strip().lower()
    base_type = normalize_website_game_type(raw_type)
    copied = dict(game)
    copied["raw_game_type"] = raw_type
    copied["base_game_type"] = base_type
    copied["game_type"] = base_type
    copied["game_display_name"] = normalize_website_game_display_name(raw_type, game.get("game_display_name"))
    copied["result_platform"] = platform
    if is_noncanonical_record_game_type(raw_type) and copied.get("non_scoring"):
        copied["non_scoring"] = False
    return copied


def build_platform_game_buckets(
    games: Iterable[dict[str, Any]],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    post_keys = load_platform_post_keys(repo_root)
    buckets: dict[str, list[dict[str, Any]]] = {platform: [] for platform in WEBSITE_PLATFORMS}
    seen: set[tuple[str, str]] = set()
    for game in games:
        if not isinstance(game, dict):
            continue
        game_id = str(game.get("game_id") or "").strip()
        if not game_id:
            continue
        for platform in sorted(classify_game_platforms(game, post_keys)):
            dedupe_key = (platform, game_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            buckets[platform].append(_platform_game_copy(game, platform))
    for platform in WEBSITE_PLATFORMS:
        buckets[platform].sort(key=lambda item: (str(item.get("timestamp") or ""), str(item.get("game_id") or "")))
    return buckets


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _write_json_if_changed(path: Path, payload: Any) -> bool:
    serialized = _json_bytes(payload)
    try:
        if path.exists() and path.read_bytes() == serialized:
            return False
    except Exception:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    results_store.atomic_write_json(path, payload)
    return True


def _remove_stale_json(directory: Path, expected_files: set[str], pattern: re.Pattern[str] | None = None) -> list[Path]:
    removed: list[Path] = []
    if not directory.exists():
        return removed
    for path in directory.glob("*.json"):
        if pattern is not None and not pattern.match(path.name):
            continue
        if path.name in expected_files:
            continue
        try:
            path.unlink()
            removed.append(path)
        except Exception:
            continue
    return removed


def _month_bucket() -> dict[str, Any]:
    return {
        "points": 0.0,
        "games": 0,
        "wins": 0,
        "best_placement": float("inf"),
        "total_kills": 0,
        "total_placement": 0,
    }


def _serialize_month_leaderboard(
    month_key: str,
    game_type: str,
    players: dict[str, dict[str, Any]],
    *,
    preview_limit: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    leaderboard: list[dict[str, Any]] = []
    for username, stats in players.items():
        best = stats.get("best_placement", float("inf"))
        leaderboard.append(
            {
                "u": username,
                "p": round(float(stats.get("points") or 0.0), 1),
                "g": int(stats.get("games") or 0),
                "w": int(stats.get("wins") or 0),
                "b": 0 if best == float("inf") else int(best or 0),
                "k": int(stats.get("total_kills") or 0),
                "t": int(stats.get("total_placement") or 0),
            }
        )
    leaderboard.sort(key=lambda item: (-float(item.get("p") or 0.0), str(item.get("u") or "")))
    for rank, entry in enumerate(leaderboard, start=1):
        entry["r"] = rank
    payload = {
        "month": month_key,
        "game_type": game_type,
        "total_players": len(leaderboard),
        "leaderboard": leaderboard,
    }
    preview = None
    if preview_limit > 0 and len(leaderboard) > preview_limit:
        preview = {
            "month": month_key,
            "game_type": game_type,
            "total_players": len(leaderboard),
            "is_preview": True,
            "preview_limit": preview_limit,
            "total_results": len(leaderboard),
            "leaderboard": leaderboard[:preview_limit],
        }
    return payload, preview


def _normalize_letter(username: str) -> str:
    first = str(username or "")[:1].lower()
    return first if first.isalpha() else "0"


def _safe_avatar_name(username: str) -> str:
    cleaned = []
    for char in str(username or ""):
        if char.isalnum() or char in ("_", "-", "."):
            cleaned.append(char)
        else:
            cleaned.append("_")
    return "".join(cleaned) or "user"


def _find_avatar_file(cache_dir: Path, username: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = cache_dir / f"{username}{ext}"
        if candidate.exists():
            return candidate
    matches = list(cache_dir.glob(f"{username}.*"))
    return matches[0] if matches else None


def _copy_avatar(base_api_dir: Path, avatar_cache_dir: Path, username: str, changed_paths: set[Path]) -> str | None:
    if not avatar_cache_dir.exists():
        return None
    source = _find_avatar_file(avatar_cache_dir, username)
    if source is None:
        return None
    destination = base_api_dir / "avatars" / f"{_safe_avatar_name(username)}{source.suffix.lower()}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        changed = True
        if destination.exists() and source.stat().st_size == destination.stat().st_size:
            changed = source.read_bytes() != destination.read_bytes()
        if changed:
            shutil.copy2(source, destination)
            changed_paths.add(destination)
        return f"api/avatars/{destination.name}"
    except Exception:
        return None


def _stats_entry() -> list[Any]:
    return [0.0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0.0]


def _build_player_stats(scoring_games: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    players: dict[str, dict[str, Any]] = {}
    for game in sorted(scoring_games, key=lambda item: str(item.get("timestamp") or "")):
        game_type = str(game.get("game_type") or "")
        game_id = str(game.get("game_id") or "")
        total_participants = int(game.get("total_participants") or len(game.get("results") or []))
        for result in game.get("results") or []:
            username = str(result.get("username") or "").strip()
            if not username:
                continue
            entry = players.setdefault(username, {"s": _stats_entry(), "gb": {}, "rg": []})
            stats = entry["s"]
            placement = int(result.get("placement") or result.get("rank") or 0)
            points = float(result.get("points") or 0.0)
            kills = int(result.get("kills") or 0)
            survival_time = float(result.get("survival_time") or 0.0)
            damage = float(result.get("damage", result.get("damage_dealt", 0.0)) or 0.0)

            stats[0] = round(float(stats[0]) + points, 1)
            stats[1] += 1
            if int(stats[2]) == 0 or (placement > 0 and placement < int(stats[2])):
                stats[2] = placement
            stats[3] += placement
            if placement == 1:
                stats[4] += 1
            if placement <= 3:
                stats[5] += 1
            top_10_threshold = max(1, int(total_participants * 0.1))
            if placement > 0 and placement <= top_10_threshold:
                stats[6] += 1
                stats[9] += 1
                stats[10] = max(stats[10], stats[9])
            else:
                stats[9] = 0
            stats[7] = round(float(stats[7]) + survival_time, 1)
            if placement == total_participants:
                stats[8] += 1
            stats[11] += kills
            stats[12] = round(float(stats[12]) + damage, 1)
            if game_type:
                entry["gb"][game_type] = int(entry["gb"].get(game_type) or 0) + 1
            if game_id and game_id not in entry["rg"]:
                entry["rg"].insert(0, game_id)
                entry["rg"] = entry["rg"][:20]

    player_index: list[dict[str, Any]] = []
    for username, entry in players.items():
        stats = entry["s"]
        letter = _normalize_letter(username)
        player_index.append(
            {
                "u": username,
                "p": round(float(stats[0]), 1),
                "g": int(stats[1]),
                "w": int(stats[4]),
                "b": int(stats[2]),
                "t": int(stats[3]),
                "k": int(stats[11]),
                "t3": int(stats[5]),
                "t10": int(stats[6]),
                "l": letter,
            }
        )
    player_index.sort(key=lambda item: (-float(item.get("p") or 0.0), str(item.get("u") or "")))
    return players, player_index


def _export_single_platform(
    root: Path,
    platform: str,
    games: list[dict[str, Any]],
    *,
    base_api_dir: Path,
    avatar_cache_dir: Path,
    preview_limit: int,
    total_followers: int,
) -> tuple[dict[str, Any], set[Path]]:
    changed_paths: set[Path] = set()
    root.mkdir(parents=True, exist_ok=True)
    games_dir = root / "games"
    days_dir = root / "days"
    types_dir = root / "types"
    leaderboards_dir = root / "leaderboards"
    players_dir = root / "players"
    history_dir = root / "player_history"
    for directory in (games_dir, days_dir, types_dir, leaderboards_dir, players_dir, history_dir):
        directory.mkdir(parents=True, exist_ok=True)

    non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])
    games_by_day: dict[int, list[dict[str, Any]]] = defaultdict(list)
    games_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_days: set[int] = set()
    all_types: set[str] = set()

    expected_game_files: set[str] = set()
    for game in games:
        game_id = str(game.get("game_id") or "").strip()
        if not game_id:
            continue
        day_number = int(game.get("day_number") or 0)
        game_type = str(game.get("game_type") or "").strip()

        game_path = games_dir / f"{game_id}.json"
        if _write_json_if_changed(game_path, game):
            changed_paths.add(game_path)
        expected_game_files.add(game_path.name)

        results = list(game.get("results") or [])
        preview = {
            "game_id": game_id,
            "game_type": game_type,
            "raw_game_type": game.get("raw_game_type"),
            "base_game_type": game.get("base_game_type"),
            "game_display_name": game.get("game_display_name"),
            "day_number": game.get("day_number"),
            "timestamp": game.get("timestamp"),
            "total_participants": game.get("total_participants"),
            "results": results[:preview_limit] if preview_limit > 0 else results,
            "non_scoring": bool(game.get("non_scoring", False)),
            "result_platform": platform,
            "is_preview": preview_limit > 0,
            "preview_limit": preview_limit,
            "total_results": len(results),
        }
        preview_path = games_dir / f"{game_id}_top.json"
        if _write_json_if_changed(preview_path, preview):
            changed_paths.add(preview_path)
        expected_game_files.add(preview_path.name)

        if day_number > 0:
            games_by_day[day_number].append(game)
            all_days.add(day_number)
        if game_type:
            games_by_type[game_type].append(game)
            all_types.add(game_type)

    changed_paths.update(_remove_stale_json(games_dir, expected_game_files))

    day_metadata: list[dict[str, Any]] = []
    expected_day_files: set[str] = set()
    for day_number in sorted(all_days):
        day_games = sorted(games_by_day[day_number], key=lambda item: (str(item.get("timestamp") or ""), str(item.get("game_id") or "")))
        day_summary = {
            "platform": platform,
            "day_number": day_number,
            "total_games": len(day_games),
            "games": [
                {
                    "game_id": game.get("game_id"),
                    "game_type": game.get("game_type"),
                    "raw_game_type": game.get("raw_game_type"),
                    "base_game_type": game.get("base_game_type"),
                    "game_display_name": game.get("game_display_name"),
                    "timestamp": game.get("timestamp"),
                    "total_participants": game.get("total_participants"),
                    "non_scoring": bool(game.get("non_scoring", False)),
                    "result_platform": platform,
                }
                for game in day_games
            ],
        }
        day_path = days_dir / f"{day_number}.json"
        if _write_json_if_changed(day_path, day_summary):
            changed_paths.add(day_path)
        expected_day_files.add(day_path.name)

        scoring_games = [
            game for game in day_games
            if not game.get("non_scoring") and str(game.get("game_type") or "") not in non_scoring_types
        ]
        aggregate = _build_day_aggregate(platform, day_number, scoring_games, preview_limit)
        aggregate_path = days_dir / f"{day_number}_aggregate.json"
        if _write_json_if_changed(aggregate_path, aggregate[0]):
            changed_paths.add(aggregate_path)
        expected_day_files.add(aggregate_path.name)
        if aggregate[1] is not None:
            aggregate_preview_path = days_dir / f"{day_number}_aggregate_top.json"
            if _write_json_if_changed(aggregate_preview_path, aggregate[1]):
                changed_paths.add(aggregate_preview_path)
            expected_day_files.add(aggregate_preview_path.name)

        participants = {
            str(result.get("username") or "")
            for game in day_games
            for result in (game.get("results") or [])
            if str(result.get("username") or "").strip()
        }
        day_metadata.append(
            {
                "day": day_number,
                "games": len(day_games),
                "types": sorted({str(game.get("game_type") or "") for game in day_games if game.get("game_type")}),
                "participants": len(participants),
            }
        )

    changed_paths.update(_remove_stale_json(days_dir, expected_day_files))

    type_metadata: list[dict[str, Any]] = []
    expected_type_files: set[str] = set()
    for game_type in sorted(all_types):
        type_games = sorted(games_by_type[game_type], key=lambda item: str(item.get("timestamp") or ""), reverse=True)
        type_payload = {
            "platform": platform,
            "game_type": game_type,
            "total_games": len(type_games),
            "games": [
                {
                    "game_id": game.get("game_id"),
                    "day_number": game.get("day_number"),
                    "timestamp": game.get("timestamp"),
                    "total_participants": game.get("total_participants"),
                    "raw_game_type": game.get("raw_game_type"),
                }
                for game in type_games
            ],
        }
        type_path = types_dir / f"{game_type}.json"
        if _write_json_if_changed(type_path, type_payload):
            changed_paths.add(type_path)
        expected_type_files.add(type_path.name)
        type_metadata.append({"type": game_type, "games": len(type_games)})

    changed_paths.update(_remove_stale_json(types_dir, expected_type_files))

    scoring_games = [
        game for game in games
        if not game.get("non_scoring") and str(game.get("game_type") or "") not in non_scoring_types
    ]
    available_months = _export_monthly_leaderboards(leaderboards_dir, platform, scoring_games, preview_limit, changed_paths)
    _export_player_history(history_dir, games, changed_paths)
    _export_player_stats(players_dir, leaderboards_dir, scoring_games, preview_limit, changed_paths)
    _export_hall_of_fame(root, base_api_dir, avatar_cache_dir, platform, scoring_games, available_months, changed_paths)

    index_payload = {
        "platform": platform,
        "platform_label": PLATFORM_LABELS[platform],
        "last_updated": datetime.now().isoformat(),
        "total_games": len(games),
        "total_days": len(all_days),
        "total_followers": total_followers,
        "results_preview_limit": preview_limit,
        "available_days": sorted(all_days),
        "days_metadata": day_metadata,
        "game_types": sorted(all_types),
        "types_metadata": type_metadata,
        "available_months": available_months,
    }
    index_path = root / "index.json"
    if _write_json_if_changed(index_path, index_payload):
        changed_paths.add(index_path)
    return index_payload, changed_paths


def _build_day_aggregate(
    platform: str,
    day_number: int,
    scoring_games: list[dict[str, Any]],
    preview_limit: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    aggregated: dict[str, dict[str, Any]] = {}
    latest_timestamp = ""
    for game in scoring_games:
        timestamp = str(game.get("timestamp") or "")
        if timestamp > latest_timestamp:
            latest_timestamp = timestamp
        for result in game.get("results") or []:
            username = str(result.get("username") or "").strip()
            if not username:
                continue
            entry = aggregated.setdefault(
                username,
                {"username": username, "points": 0.0, "kills": 0, "survival_time": 0.0, "appearances": 0},
            )
            entry["points"] += float(result.get("points") or 0.0)
            entry["kills"] += int(result.get("kills") or 0)
            entry["survival_time"] += float(result.get("survival_time") or 0.0)
            entry["appearances"] += 1

    results = sorted(
        (
            {
                "username": username,
                "points": round(values["points"], 1),
                "kills": values["kills"],
                "survival_time": round(values["survival_time"], 1),
                "appearances": values["appearances"],
            }
            for username, values in aggregated.items()
        ),
        key=lambda item: (-float(item.get("points") or 0.0), str(item.get("username") or "")),
    )
    payload = {
        "platform": platform,
        "game_id": f"{platform}_all_day_{day_number}",
        "game_type": "all",
        "game_display_name": "All Games",
        "day_number": day_number,
        "timestamp": latest_timestamp,
        "total_participants": len(results),
        "results": results,
    }
    preview = None
    if preview_limit > 0 and len(results) > preview_limit:
        preview = {
            "platform": platform,
            "game_id": payload["game_id"],
            "game_type": "all",
            "game_display_name": "All Games",
            "day_number": day_number,
            "timestamp": latest_timestamp,
            "total_participants": len(results),
            "is_preview": True,
            "preview_limit": preview_limit,
            "total_results": len(results),
            "results": results[:preview_limit],
        }
    return payload, preview


def _export_monthly_leaderboards(
    leaderboards_dir: Path,
    platform: str,
    scoring_games: list[dict[str, Any]],
    preview_limit: int,
    changed_paths: set[Path],
) -> list[str]:
    monthly_data: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(_month_bucket))
    monthly_by_type: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(_month_bucket)))
    for game in scoring_games:
        timestamp = str(game.get("timestamp") or "")
        if len(timestamp) < 7:
            continue
        month_key = timestamp[:7]
        game_type = str(game.get("game_type") or "")
        for result in game.get("results") or []:
            username = str(result.get("username") or "").strip()
            if not username:
                continue
            placement = int(result.get("placement") or result.get("rank") or 0)
            points = float(result.get("points") or 0.0)
            kills = int(result.get("kills") or 0)
            for bucket in (monthly_data[month_key][username], monthly_by_type[month_key][game_type][username]):
                bucket["points"] += points
                bucket["games"] += 1
                bucket["wins"] += 1 if placement == 1 else 0
                bucket["best_placement"] = min(bucket["best_placement"], placement or float("inf"))
                bucket["total_kills"] += kills
                bucket["total_placement"] += placement

    expected_files: set[str] = set()
    for month_key, players in sorted(monthly_data.items()):
        payload, preview = _serialize_month_leaderboard(month_key, "all", players, preview_limit=preview_limit)
        payload["platform"] = platform
        path = leaderboards_dir / f"{month_key}.json"
        if _write_json_if_changed(path, payload):
            changed_paths.add(path)
        expected_files.add(path.name)
        if preview is not None:
            preview["platform"] = platform
            preview_path = leaderboards_dir / f"{month_key}_top.json"
            if _write_json_if_changed(preview_path, preview):
                changed_paths.add(preview_path)
            expected_files.add(preview_path.name)
    for month_key, typed in sorted(monthly_by_type.items()):
        for game_type, players in sorted(typed.items()):
            payload, preview = _serialize_month_leaderboard(month_key, game_type, players, preview_limit=preview_limit)
            payload["platform"] = platform
            path = leaderboards_dir / f"{month_key}_{game_type}.json"
            if _write_json_if_changed(path, payload):
                changed_paths.add(path)
            expected_files.add(path.name)
            if preview is not None:
                preview["platform"] = platform
                preview_path = leaderboards_dir / f"{month_key}_{game_type}_top.json"
                if _write_json_if_changed(preview_path, preview):
                    changed_paths.add(preview_path)
                expected_files.add(preview_path.name)
    monthly_pattern = re.compile(r"^\d{4}-\d{2}(?:_.+)?(?:_top)?\.json$")
    changed_paths.update(_remove_stale_json(leaderboards_dir, expected_files, monthly_pattern))
    return sorted(monthly_data.keys())


def _export_player_history(history_dir: Path, games: list[dict[str, Any]], changed_paths: set[Path]) -> None:
    histories: dict[str, dict[str, list[list[int]]]] = defaultdict(lambda: defaultdict(list))
    game_meta: list[list[Any]] = []
    for game in sorted(games, key=lambda item: str(item.get("timestamp") or ""), reverse=True):
        game_id = str(game.get("game_id") or "").strip()
        if not game_id:
            continue
        game_index = len(game_meta)
        game_meta.append([game_id, game.get("game_type"), game.get("day_number"), game.get("timestamp")])
        for result in game.get("results") or []:
            username = str(result.get("username") or "").strip()
            if not username:
                continue
            histories[_normalize_letter(username)][username].append(
                [
                    game_index,
                    int(result.get("placement") or result.get("rank") or 0),
                    int(round(float(result.get("points") or 0.0) * DEFAULT_POINTS_SCALE)),
                    int(result.get("kills") or 0),
                ]
            )

    expected_files = {"index.json"}
    for letter, players in sorted(histories.items()):
        path = history_dir / f"{letter}.json"
        payload = {"letter": letter, "count": len(players), "players": players}
        if _write_json_if_changed(path, payload):
            changed_paths.add(path)
        expected_files.add(path.name)
    index_payload = {
        "lu": datetime.now().isoformat(),
        "points_scale": DEFAULT_POINTS_SCALE,
        "game_count": len(game_meta),
        "games": game_meta,
    }
    index_path = history_dir / "index.json"
    if _write_json_if_changed(index_path, index_payload):
        changed_paths.add(index_path)
    changed_paths.update(_remove_stale_json(history_dir, expected_files))


def _export_player_stats(
    players_dir: Path,
    leaderboards_dir: Path,
    scoring_games: list[dict[str, Any]],
    preview_limit: int,
    changed_paths: set[Path],
) -> None:
    players, player_index = _build_player_stats(scoring_games)
    players_by_letter: dict[str, dict[str, Any]] = defaultdict(dict)
    for username, entry in players.items():
        compact = {"s": entry["s"]}
        if entry["gb"]:
            compact["gb"] = entry["gb"]
        if entry["rg"]:
            compact["rg"] = entry["rg"]
        players_by_letter[_normalize_letter(username)][username] = compact

    expected_player_files = {"index.json"}
    for letter, letter_players in sorted(players_by_letter.items()):
        path = players_dir / f"{letter}.json"
        payload = {"letter": letter, "count": len(letter_players), "players": letter_players}
        if _write_json_if_changed(path, payload):
            changed_paths.add(path)
        expected_player_files.add(path.name)
    index_path = players_dir / "index.json"
    index_payload = {
        "lu": datetime.now().isoformat(),
        "tgr": len(scoring_games),
        "total_players": len(player_index),
        "letters": sorted(players_by_letter.keys()),
        "players": player_index,
    }
    if _write_json_if_changed(index_path, index_payload):
        changed_paths.add(index_path)
    changed_paths.update(_remove_stale_json(players_dir, expected_player_files))

    leaderboard = []
    for rank, entry in enumerate(player_index, start=1):
        leaderboard.append(
            {
                "u": entry["u"],
                "p": round(float(entry.get("p") or 0.0), 1),
                "g": int(entry.get("g") or 0),
                "w": int(entry.get("w") or 0),
                "b": int(entry.get("b") or 0),
                "t": int(entry.get("t") or 0),
                "k": int(entry.get("k") or 0),
                "t3": int(entry.get("t3") or 0),
                "t10": int(entry.get("t10") or 0),
                "r": rank,
            }
        )
    payload = {
        "scope": "all_time",
        "lu": datetime.now().isoformat(),
        "total_players": len(leaderboard),
        "leaderboard": leaderboard,
    }
    path = leaderboards_dir / "all_time.json"
    if _write_json_if_changed(path, payload):
        changed_paths.add(path)
    if preview_limit > 0 and len(leaderboard) > preview_limit:
        preview = {
            "scope": "all_time",
            "lu": payload["lu"],
            "total_players": len(leaderboard),
            "is_preview": True,
            "preview_limit": preview_limit,
            "total_results": len(leaderboard),
            "leaderboard": leaderboard[:preview_limit],
        }
        preview_path = leaderboards_dir / "all_time_top.json"
        if _write_json_if_changed(preview_path, preview):
            changed_paths.add(preview_path)


def _export_hall_of_fame(
    root: Path,
    base_api_dir: Path,
    avatar_cache_dir: Path,
    platform: str,
    scoring_games: list[dict[str, Any]],
    available_months: list[str],
    changed_paths: set[Path],
) -> None:
    daily_points: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    daily_timestamps: dict[int, str] = {}
    monthly_points: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for game in scoring_games:
        day_number = int(game.get("day_number") or 0)
        timestamp = str(game.get("timestamp") or "")
        if day_number > 0 and timestamp > daily_timestamps.get(day_number, ""):
            daily_timestamps[day_number] = timestamp
        for result in game.get("results") or []:
            username = str(result.get("username") or "").strip()
            if not username:
                continue
            points = float(result.get("points") or 0.0)
            if day_number > 0:
                daily_points[day_number][username] += points
            if len(timestamp) >= 7:
                monthly_points[timestamp[:7]][username] += points

    def pick(points: dict[str, float]) -> tuple[str, float] | None:
        if not points:
            return None
        return sorted(points.items(), key=lambda item: (-float(item[1]), item[0]))[0]

    daily_champions = []
    for day_number, points in sorted(daily_points.items(), reverse=True):
        champion = pick(points)
        if champion is None:
            continue
        daily_champions.append(
            {
                "day": day_number,
                "username": champion[0],
                "points": round(champion[1], 2),
                "timestamp": daily_timestamps.get(day_number, ""),
                "platform": platform,
            }
        )
    monthly_champions = []
    for month_key in sorted(set(available_months) | set(monthly_points.keys()), reverse=True):
        champion = pick(monthly_points.get(month_key, {}))
        if champion is None:
            continue
        monthly_champions.append(
            {
                "month": month_key,
                "username": champion[0],
                "points": round(champion[1], 2),
                "platform": platform,
            }
        )

    for entry in daily_champions + monthly_champions:
        entry["avatar"] = _copy_avatar(base_api_dir, avatar_cache_dir, str(entry.get("username") or ""), changed_paths)

    payload = {
        "last_updated": datetime.now().isoformat(),
        "platform": platform,
        "daily_champions": daily_champions,
        "monthly_champions": monthly_champions,
    }
    path = root / "hall_of_fame.json"
    if _write_json_if_changed(path, payload):
        changed_paths.add(path)


def export_platform_partitions(
    base_api_dir: str | Path,
    games: Iterable[dict[str, Any]],
    *,
    repo_root: str | Path | None = None,
    avatar_cache_dir: str | Path = "avatar_cache",
    preview_limit: int | None = None,
    total_followers: int = 0,
) -> tuple[list[dict[str, Any]], set[Path]]:
    base_path = Path(base_api_dir)
    root = base_path / "platforms"
    root.mkdir(parents=True, exist_ok=True)
    resolved_preview_limit = int(preview_limit if preview_limit is not None else getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0)
    repo = Path(repo_root or getattr(config, "PROJECT_ROOT", ".")).resolve()
    avatar_path = Path(avatar_cache_dir)
    if not avatar_path.is_absolute():
        avatar_path = repo / avatar_path

    buckets = build_platform_game_buckets(games, repo_root=repo)
    changed_paths: set[Path] = set()
    metadata: list[dict[str, Any]] = []
    for platform in WEBSITE_PLATFORMS:
        index_payload, platform_changes = _export_single_platform(
            root / platform,
            platform,
            buckets.get(platform, []),
            base_api_dir=base_path,
            avatar_cache_dir=avatar_path,
            preview_limit=resolved_preview_limit,
            total_followers=total_followers,
        )
        changed_paths.update(platform_changes)
        metadata.append(
            {
                "platform": platform,
                "label": PLATFORM_LABELS[platform],
                "total_games": index_payload["total_games"],
                "total_days": index_payload["total_days"],
                "available_days": index_payload["available_days"],
                "available_months": index_payload["available_months"],
                "types_metadata": index_payload["types_metadata"],
            }
        )
    return metadata, changed_paths
