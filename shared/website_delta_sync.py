from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import config
from . import cloud_sync, media_kit, results_store
from .game_history import GameHistory
from .platform_targets import is_noncanonical_record_game_type
from .website_platforms import export_platform_partitions


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_DIR = REPO_ROOT / "website" / "public"
DEFAULT_API_DIR = DEFAULT_PUBLIC_DIR / "api"
DEFAULT_EVENTS_DAYS_DIR = REPO_ROOT / "backups" / "game_results" / "events" / "days"
DEFAULT_EVENTS_GAMES_DIR = REPO_ROOT / "backups" / "game_results" / "events" / "games"
DEFAULT_AVATAR_CACHE_DIR = REPO_ROOT / "avatar_cache"
DEFAULT_SYNC_STATE_PATH = REPO_ROOT / "logs" / "website_sync" / "state.json"
DEFAULT_POINTS_SCALE = 10
PLAYER_STATS_FIELDS = 13


@dataclass
class WebsiteSyncResult:
    day_number: int
    ok: bool
    changed_api_paths: list[str]
    changed_count: int
    published: bool
    publish_message: str
    new_game_ids: list[str]
    output_excerpt: str = ""


def _normalize_letter(username: str) -> str:
    first = str(username or "")[:1].lower()
    return first if first.isalpha() else "0"


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


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


def _copy_file_if_changed(source: Path, destination: Path) -> bool:
    if not source.exists():
        raise FileNotFoundError(f"Missing source file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        if destination.exists() and source.stat().st_size == destination.stat().st_size:
            if source.read_bytes() == destination.read_bytes():
                return False
    except Exception:
        pass
    shutil.copy2(source, destination)
    return True


def _to_api_relative(path: Path, api_dir: Path) -> str:
    return path.resolve().relative_to(api_dir.resolve()).as_posix()


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


def _compact_player_entry(entry: Any) -> dict[str, Any]:
    if isinstance(entry, dict):
        stats = list(entry.get("s") or [])
        breakdown = dict(entry.get("gb") or {})
        recent = list(entry.get("rg") or [])
    else:
        stats = []
        breakdown = {}
        recent = []
    while len(stats) < PLAYER_STATS_FIELDS:
        stats.append(0)
    return {"s": stats[:PLAYER_STATS_FIELDS], "gb": breakdown, "rg": recent}


def _month_bucket() -> dict[str, Any]:
    return {
        "points": 0.0,
        "games": 0,
        "wins": 0,
        "best_placement": float("inf"),
        "total_kills": 0,
        "total_placement": 0,
    }


def _load_month_leaderboard_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(path, {})
    leaderboard = payload.get("leaderboard") if isinstance(payload, dict) else []
    mapped: dict[str, dict[str, Any]] = {}
    for entry in leaderboard or []:
        username = str(entry.get("u") or "").strip()
        if not username:
            continue
        mapped[username] = {
            "points": float(entry.get("p") or 0.0),
            "games": int(entry.get("g") or 0),
            "wins": int(entry.get("w") or 0),
            "best_placement": int(entry.get("b") or 0) or float("inf"),
            "total_kills": int(entry.get("k") or 0),
            "total_placement": int(entry.get("t") or 0),
        }
    return mapped


def _serialize_month_leaderboard(
    month_key: str,
    game_type: str,
    players: dict[str, dict[str, Any]],
    *,
    preview_limit: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    leaderboard: list[dict[str, Any]] = []
    for username, stats in players.items():
        leaderboard.append(
            {
                "u": username,
                "p": round(float(stats.get("points") or 0.0), 1),
                "g": int(stats.get("games") or 0),
                "w": int(stats.get("wins") or 0),
                "b": 0
                if stats.get("best_placement", float("inf")) == float("inf")
                else int(stats.get("best_placement") or 0),
                "k": int(stats.get("total_kills") or 0),
                "t": int(stats.get("total_placement") or 0),
            }
        )

    leaderboard.sort(key=lambda item: (-float(item["p"]), str(item["u"])))
    for index, entry in enumerate(leaderboard, start=1):
        entry["r"] = index

    payload = {
        "month": month_key,
        "game_type": game_type,
        "total_players": len(leaderboard),
        "leaderboard": leaderboard,
    }

    preview_payload = None
    if preview_limit > 0 and len(leaderboard) > preview_limit:
        preview_payload = {
            "month": month_key,
            "game_type": game_type,
            "total_players": len(leaderboard),
            "is_preview": True,
            "preview_limit": preview_limit,
            "total_results": len(leaderboard),
            "leaderboard": leaderboard[:preview_limit],
        }
    return payload, preview_payload


def _load_player_index_map(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    payload = _load_json(path, {})
    players = payload.get("players") if isinstance(payload, dict) else []
    mapped: dict[str, dict[str, Any]] = {}
    for entry in players or []:
        username = str(entry.get("u") or "").strip()
        if not username:
            continue
        mapped[username] = dict(entry)
    return mapped, payload if isinstance(payload, dict) else {}


def _history_entry_payload(
    game_index: int,
    placement: int,
    points_scaled: int,
    kills: int,
) -> list[int]:
    return [int(game_index), int(placement), int(points_scaled), int(kills)]


class WebsiteDeltaSync:
    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        api_dir: Path | None = None,
        public_dir: Path | None = None,
        events_days_dir: Path | None = None,
        events_games_dir: Path | None = None,
        avatar_cache_dir: Path | None = None,
        sync_state_path: Path | None = None,
        preview_limit: int | None = None,
    ):
        self.repo_root = (repo_root or REPO_ROOT).resolve()
        self.public_dir = (public_dir or (self.repo_root / "website" / "public")).resolve()
        self.api_dir = (api_dir or (self.public_dir / "api")).resolve()
        self.events_days_dir = (events_days_dir or DEFAULT_EVENTS_DAYS_DIR).resolve()
        self.events_games_dir = (events_games_dir or DEFAULT_EVENTS_GAMES_DIR).resolve()
        self.avatar_cache_dir = (avatar_cache_dir or DEFAULT_AVATAR_CACHE_DIR).resolve()
        self.sync_state_path = (sync_state_path or DEFAULT_SYNC_STATE_PATH).resolve()
        self.preview_limit = int(
            preview_limit if preview_limit is not None else getattr(config, "WEB_RESULTS_PREVIEW_LIMIT", 200) or 0
        )
        self.non_scoring_types = set(getattr(config, "NON_SCORING_GAME_TYPES", []) or [])

    def load_sync_state(self) -> dict[str, Any]:
        default = {
            "last_day_synced": 0,
            "days_synced": [],
            "last_run_at": "",
            "last_error": "",
            "last_published_at": "",
        }
        state = _load_json(self.sync_state_path, default)
        if not isinstance(state, dict):
            return dict(default)
        for key, value in default.items():
            state.setdefault(key, value)
        return state

    def _save_sync_state(self, payload: dict[str, Any]) -> None:
        self.sync_state_path.parent.mkdir(parents=True, exist_ok=True)
        results_store.atomic_write_json(self.sync_state_path, payload)

    def _load_day_entries(self, day_number: int) -> list[dict[str, Any]]:
        path = self.events_days_dir / f"{int(day_number)}.json"
        payload = _load_json(path, {})
        games = payload.get("games") if isinstance(payload, dict) else []
        canonical: list[dict[str, Any]] = []
        seen_game_ids: set[str] = set()
        for entry in games or []:
            if not isinstance(entry, dict):
                continue
            game_id = str(entry.get("game_id") or "").strip()
            game_type = str(entry.get("game_type") or "").strip().lower()
            if not game_id or game_id in seen_game_ids or is_noncanonical_record_game_type(game_type):
                continue
            seen_game_ids.add(game_id)
            canonical.append(
                {
                    "game_id": game_id,
                    "game_type": game_type,
                    "game_display_name": entry.get("game_display_name"),
                    "timestamp": str(entry.get("timestamp") or ""),
                    "total_participants": int(entry.get("total_participants") or 0),
                    "day_number": int(day_number),
                    "non_scoring": bool(entry.get("non_scoring", False)),
                }
            )
        canonical.sort(key=lambda item: (item.get("timestamp") or "", item.get("game_id") or ""))
        return canonical

    def _load_all_event_games(self) -> list[dict[str, Any]]:
        games: list[dict[str, Any]] = []
        if not self.events_games_dir.exists():
            return games
        for path in sorted(self.events_games_dir.glob("*.json")):
            payload = _load_json(path, {})
            if isinstance(payload, dict) and str(payload.get("game_id") or "").strip():
                games.append(payload)
        return games

    def _build_game_preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        results = list(payload.get("results") or [])
        return {
            "game_id": payload.get("game_id"),
            "game_type": payload.get("game_type"),
            "game_display_name": payload.get("game_display_name"),
            "day_number": payload.get("day_number"),
            "timestamp": payload.get("timestamp"),
            "total_participants": payload.get("total_participants"),
            "results": results[: self.preview_limit] if self.preview_limit > 0 else results,
            "non_scoring": bool(payload.get("non_scoring", False)),
            "is_preview": self.preview_limit > 0,
            "preview_limit": self.preview_limit,
            "total_results": len(results),
        }

    def _build_day_summary(
        self,
        day_number: int,
        summaries: list[dict[str, Any]],
        participant_count: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        game_types: set[str] = set()
        for summary in summaries:
            game_types.add(str(summary.get("game_type") or ""))
        day_summary = {
            "day_number": int(day_number),
            "total_games": len(summaries),
            "games": [
                {
                    "game_id": item.get("game_id"),
                    "game_type": item.get("game_type"),
                    "game_display_name": item.get("game_display_name"),
                    "timestamp": item.get("timestamp"),
                    "total_participants": item.get("total_participants"),
                    "non_scoring": bool(item.get("non_scoring", False)),
                }
                for item in summaries
            ],
        }
        day_meta = {
            "day": int(day_number),
            "games": len(summaries),
            "types": sorted(game_type for game_type in game_types if game_type),
            "participants": int(participant_count),
        }
        return day_summary, day_meta

    def _build_day_aggregate(self, day_number: int, scoring_games: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        aggregated: dict[str, dict[str, Any]] = {}
        latest_timestamp = ""
        for payload in scoring_games:
            timestamp = str(payload.get("timestamp") or "")
            if timestamp > latest_timestamp:
                latest_timestamp = timestamp
            for result in payload.get("results") or []:
                username = str(result.get("username") or "").strip()
                if not username:
                    continue
                entry = aggregated.setdefault(
                    username,
                    {
                        "username": username,
                        "points": 0.0,
                        "kills": 0,
                        "survival_time": 0.0,
                        "appearances": 0,
                    },
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
            "game_id": f"all_day_{int(day_number)}",
            "game_type": "all",
            "game_display_name": "All Games",
            "day_number": int(day_number),
            "timestamp": latest_timestamp or "",
            "total_participants": len(results),
            "results": results,
        }

        preview_payload = None
        if self.preview_limit > 0 and len(results) > self.preview_limit:
            preview_payload = {
                "game_id": payload["game_id"],
                "game_type": payload["game_type"],
                "game_display_name": payload["game_display_name"],
                "day_number": payload["day_number"],
                "timestamp": payload["timestamp"],
                "total_participants": payload["total_participants"],
                "is_preview": True,
                "preview_limit": self.preview_limit,
                "total_results": len(results),
                "results": results[: self.preview_limit],
            }
        return payload, preview_payload

    def _update_type_indexes(
        self,
        type_updates: dict[str, list[dict[str, Any]]],
        changed_api_paths: set[str],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        types_dir = self.api_dir / "types"
        types_dir.mkdir(parents=True, exist_ok=True)
        for game_type, summaries in type_updates.items():
            path = types_dir / f"{game_type}.json"
            payload = _load_json(path, {})
            games = payload.get("games") if isinstance(payload, dict) else []
            merged: dict[str, dict[str, Any]] = {}
            for item in games or []:
                game_id = str(item.get("game_id") or "").strip()
                if game_id:
                    merged[game_id] = dict(item)
            for summary in summaries:
                merged[str(summary.get("game_id") or "")] = {
                    "game_id": summary.get("game_id"),
                    "day_number": summary.get("day_number"),
                    "timestamp": summary.get("timestamp"),
                    "total_participants": summary.get("total_participants"),
                }
            ordered = sorted(
                merged.values(),
                key=lambda item: (str(item.get("timestamp") or ""), str(item.get("game_id") or "")),
                reverse=True,
            )
            type_payload = {
                "game_type": game_type,
                "total_games": len(ordered),
                "games": ordered,
            }
            if _write_json_if_changed(path, type_payload):
                changed_api_paths.add(_to_api_relative(path, self.api_dir))
            counts[game_type] = len(ordered)
        return counts

    def _apply_scoring_ops_to_entry(
        self,
        compact_entry: dict[str, Any],
        ops: list[tuple[int, float, float, int, int, float, str, str]],
    ) -> None:
        stats = compact_entry["s"]
        breakdown = compact_entry["gb"]
        recent = compact_entry["rg"]

        for placement, points, survival_time, total_participants, kills, damage, game_type, _game_id in ops:
            stats[0] = round(float(stats[0]) + float(points), 1)
            stats[1] += 1
            stats[3] += int(placement)
            stats[7] = round(float(stats[7]) + float(survival_time), 1)
            stats[11] += int(kills)
            stats[12] = round(float(stats[12]) + float(damage), 1)

            if int(stats[2]) == 0 or int(placement) < int(stats[2]):
                stats[2] = int(placement)
            if int(placement) == 1:
                stats[4] += 1
            if int(placement) <= 3:
                stats[5] += 1

            top_10_threshold = max(1, int(int(total_participants) * 0.1))
            if int(placement) <= top_10_threshold:
                stats[6] += 1
                stats[9] += 1
                if int(stats[9]) > int(stats[10]):
                    stats[10] = int(stats[9])
            else:
                stats[9] = 0

            if int(placement) == int(total_participants):
                stats[8] += 1

            if game_type:
                breakdown[game_type] = int(breakdown.get(game_type) or 0) + 1

        new_recent: list[str] = []
        seen_recent: set[str] = set()
        for _placement, _points, _survival_time, _total_participants, _kills, _damage, _game_type, game_id in reversed(ops):
            if not game_id or game_id in seen_recent:
                continue
            seen_recent.add(game_id)
            new_recent.append(game_id)
        compact_entry["rg"] = (new_recent + [game_id for game_id in recent if game_id not in seen_recent])[:20]

    def _update_player_stats(
        self,
        scoring_ops_by_letter: dict[str, dict[str, list[tuple[int, float, float, int, int, float, str, str]]]],
        new_scoring_games_count: int,
        changed_api_paths: set[str],
    ) -> None:
        players_dir = self.api_dir / "players"
        players_dir.mkdir(parents=True, exist_ok=True)
        index_path = players_dir / "index.json"
        player_index_map, index_payload = _load_player_index_map(index_path)
        letters = set(index_payload.get("letters") or [])
        total_games_recorded = int(index_payload.get("tgr") or 0) + int(new_scoring_games_count)

        for letter, users in scoring_ops_by_letter.items():
            path = players_dir / f"{letter}.json"
            payload = _load_json(path, {})
            players = dict(payload.get("players") or {}) if isinstance(payload, dict) else {}

            for username, ops in users.items():
                entry = _compact_player_entry(players.get(username))
                self._apply_scoring_ops_to_entry(entry, ops)
                compact = {"s": entry["s"]}
                if entry["gb"]:
                    compact["gb"] = entry["gb"]
                if entry["rg"]:
                    compact["rg"] = entry["rg"]
                players[username] = compact

                stats = entry["s"]
                player_index_map[username] = {
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

            letter_payload = {
                "letter": letter,
                "count": len(players),
                "players": players,
            }
            if _write_json_if_changed(path, letter_payload):
                changed_api_paths.add(_to_api_relative(path, self.api_dir))
            letters.add(letter)

        ordered_players = sorted(
            player_index_map.values(),
            key=lambda item: (-float(item.get("p") or 0.0), str(item.get("u") or "")),
        )
        index_output = {
            "lu": datetime.now().isoformat(),
            "tgr": total_games_recorded,
            "total_players": len(ordered_players),
            "letters": sorted(letter for letter in letters if str(letter).strip()),
            "players": ordered_players,
        }
        if _write_json_if_changed(index_path, index_output):
            changed_api_paths.add(_to_api_relative(index_path, self.api_dir))

    def _update_player_history(
        self,
        canonical_entries: list[dict[str, Any]],
        history_ops_by_letter: dict[str, dict[str, list[tuple[str, str, int, str, int, int, int]]]],
        new_game_ids: set[str],
        changed_api_paths: set[str],
    ) -> None:
        history_dir = self.api_dir / "player_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        index_path = history_dir / "index.json"
        index_payload = _load_json(index_path, {})
        existing_meta = list(index_payload.get("games") or []) if isinstance(index_payload, dict) else []
        points_scale = int(index_payload.get("points_scale") or DEFAULT_POINTS_SCALE)
        game_index_by_id = {
            str(meta[0]): idx
            for idx, meta in enumerate(existing_meta)
            if isinstance(meta, list) and meta and str(meta[0]).strip()
        }

        appended_count = 0
        for entry in canonical_entries:
            game_id = str(entry.get("game_id") or "").strip()
            if not game_id or game_id not in new_game_ids or game_id in game_index_by_id:
                continue
            game_index_by_id[game_id] = len(existing_meta)
            existing_meta.append(
                [
                    game_id,
                    str(entry.get("game_type") or ""),
                    int(entry.get("day_number") or 0),
                    str(entry.get("timestamp") or ""),
                ]
            )
            appended_count += 1

        if appended_count > 0:
            index_output = {
                "lu": datetime.now().isoformat(),
                "points_scale": points_scale,
                "game_count": len(existing_meta),
                "games": existing_meta,
            }
            if _write_json_if_changed(index_path, index_output):
                changed_api_paths.add(_to_api_relative(index_path, self.api_dir))

        for letter, users in history_ops_by_letter.items():
            path = history_dir / f"{letter}.json"
            payload = _load_json(path, {})
            players = dict(payload.get("players") or {}) if isinstance(payload, dict) else {}

            for username, entries in users.items():
                existing_entries = list(players.get(username) or [])
                existing_game_ids = set()
                for item in existing_entries:
                    if not isinstance(item, list) or not item:
                        continue
                    game_meta = existing_meta[int(item[0])] if int(item[0]) < len(existing_meta) else None
                    if isinstance(game_meta, list) and game_meta:
                        existing_game_ids.add(str(game_meta[0]))

                new_entries: list[list[int]] = []
                for game_id, _game_type, _day_number, _timestamp, placement, points_scaled, kills in reversed(entries):
                    if game_id in existing_game_ids:
                        continue
                    game_index = game_index_by_id.get(game_id)
                    if game_index is None:
                        continue
                    existing_game_ids.add(game_id)
                    new_entries.append(
                        _history_entry_payload(
                            game_index=game_index,
                            placement=placement,
                            points_scaled=points_scaled,
                            kills=kills,
                        )
                    )

                if new_entries:
                    players[username] = new_entries + existing_entries

            output = {
                "letter": letter,
                "count": len(players),
                "players": players,
            }
            if _write_json_if_changed(path, output):
                changed_api_paths.add(_to_api_relative(path, self.api_dir))

    def _update_monthly_leaderboards(
        self,
        monthly_all_deltas: dict[str, dict[str, dict[str, Any]]],
        monthly_type_deltas: dict[str, dict[str, dict[str, dict[str, Any]]]],
        changed_api_paths: set[str],
    ) -> set[str]:
        leaderboards_dir = self.api_dir / "leaderboards"
        leaderboards_dir.mkdir(parents=True, exist_ok=True)
        touched_months: set[str] = set()

        def apply_delta_to_map(
            existing: dict[str, dict[str, Any]],
            delta: dict[str, dict[str, Any]],
        ) -> dict[str, dict[str, Any]]:
            merged = {username: dict(values) for username, values in existing.items()}
            for username, bucket in delta.items():
                target = merged.setdefault(username, _month_bucket())
                target["points"] = float(target.get("points") or 0.0) + float(bucket.get("points") or 0.0)
                target["games"] = int(target.get("games") or 0) + int(bucket.get("games") or 0)
                target["wins"] = int(target.get("wins") or 0) + int(bucket.get("wins") or 0)
                best_existing = target.get("best_placement", float("inf"))
                best_delta = bucket.get("best_placement", float("inf"))
                target["best_placement"] = min(best_existing, best_delta)
                target["total_kills"] = int(target.get("total_kills") or 0) + int(bucket.get("total_kills") or 0)
                target["total_placement"] = int(target.get("total_placement") or 0) + int(
                    bucket.get("total_placement") or 0
                )
            return merged

        for month_key, delta in monthly_all_deltas.items():
            touched_months.add(month_key)
            path = leaderboards_dir / f"{month_key}.json"
            preview_path = leaderboards_dir / f"{month_key}_top.json"
            merged = apply_delta_to_map(_load_month_leaderboard_map(path), delta)
            payload, preview = _serialize_month_leaderboard(month_key, "all", merged, preview_limit=self.preview_limit)
            if _write_json_if_changed(path, payload):
                changed_api_paths.add(_to_api_relative(path, self.api_dir))
            if preview is not None:
                if _write_json_if_changed(preview_path, preview):
                    changed_api_paths.add(_to_api_relative(preview_path, self.api_dir))

        for month_key, typed_map in monthly_type_deltas.items():
            touched_months.add(month_key)
            for game_type, delta in typed_map.items():
                path = leaderboards_dir / f"{month_key}_{game_type}.json"
                preview_path = leaderboards_dir / f"{month_key}_{game_type}_top.json"
                merged = apply_delta_to_map(_load_month_leaderboard_map(path), delta)
                payload, preview = _serialize_month_leaderboard(
                    month_key,
                    game_type,
                    merged,
                    preview_limit=self.preview_limit,
                )
                if _write_json_if_changed(path, payload):
                    changed_api_paths.add(_to_api_relative(path, self.api_dir))
                if preview is not None:
                    if _write_json_if_changed(preview_path, preview):
                        changed_api_paths.add(_to_api_relative(preview_path, self.api_dir))
        return touched_months

    def _count_followers(self) -> int:
        try:
            followers_path = Path(getattr(config, "FOLLOWER_IMPORT_FILE", "Followers/new_followers_fresh.json"))
            if not followers_path.is_absolute():
                followers_path = (self.repo_root / followers_path).resolve()
            payload = _load_json(followers_path, [])
            if isinstance(payload, list):
                return len(payload)
            if isinstance(payload, dict) and isinstance(payload.get("followers"), list):
                return len(payload["followers"])
        except Exception:
            pass
        return 0

    def _refresh_index(
        self,
        day_meta: dict[str, Any],
        type_counts: dict[str, int],
        touched_months: set[str],
        changed_api_paths: set[str],
        platforms_metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        index_path = self.api_dir / "index.json"
        payload = _load_json(index_path, {})
        days_metadata = {
            int(item.get("day") or 0): dict(item)
            for item in (payload.get("days_metadata") or [])
            if isinstance(item, dict) and int(item.get("day") or 0) > 0
        }
        days_metadata[int(day_meta["day"])] = dict(day_meta)
        ordered_days = [days_metadata[key] for key in sorted(days_metadata)]

        type_metadata = {
            str(item.get("type") or ""): dict(item)
            for item in (payload.get("types_metadata") or [])
            if isinstance(item, dict) and str(item.get("type") or "").strip()
        }
        for game_type, count in type_counts.items():
            type_metadata[str(game_type)] = {"type": str(game_type), "games": int(count)}
        ordered_types = [type_metadata[key] for key in sorted(type_metadata) if key]

        available_days = sorted(item["day"] for item in ordered_days)
        available_months = set(str(value) for value in (payload.get("available_months") or []) if str(value).strip())
        available_months.update(str(value) for value in touched_months if str(value).strip())

        index_output = {
            "last_updated": datetime.now().isoformat(),
            "total_games": sum(int(item.get("games") or 0) for item in ordered_days),
            "total_days": len(available_days),
            "total_followers": self._count_followers(),
            "results_preview_limit": self.preview_limit,
            "available_days": available_days,
            "days_metadata": ordered_days,
            "game_types": [item["type"] for item in ordered_types],
            "types_metadata": ordered_types,
            "available_months": sorted(available_months),
            "platforms": platforms_metadata if platforms_metadata is not None else payload.get("platforms", []),
        }
        if _write_json_if_changed(index_path, index_output):
            changed_api_paths.add(_to_api_relative(index_path, self.api_dir))

    def _refresh_media_kit(self, changed_api_paths: set[str]) -> None:
        path = self.api_dir / "media_kit.json"
        before = path.read_bytes() if path.exists() else b""
        media_kit.export_media_kit(str(self.api_dir))
        after = path.read_bytes() if path.exists() else b""
        if before != after:
            changed_api_paths.add(_to_api_relative(path, self.api_dir))

    def _copy_hall_avatar(self, username: str, changed_api_paths: set[str]) -> str | None:
        source = _find_avatar_file(self.avatar_cache_dir, username)
        if source is None:
            return None
        avatars_dir = self.api_dir / "avatars"
        avatars_dir.mkdir(parents=True, exist_ok=True)
        destination = avatars_dir / f"{_safe_avatar_name(username)}{source.suffix.lower()}"
        if _copy_file_if_changed(source, destination):
            changed_api_paths.add(_to_api_relative(destination, self.api_dir))
        return f"api/avatars/{destination.name}"

    def _refresh_hall_of_fame(
        self,
        day_number: int,
        day_aggregate: dict[str, Any],
        touched_months: set[str],
        changed_api_paths: set[str],
    ) -> None:
        path = self.api_dir / "hall_of_fame.json"
        payload = _load_json(path, {})
        daily_champions = [dict(item) for item in (payload.get("daily_champions") or []) if isinstance(item, dict)]
        monthly_champions = [dict(item) for item in (payload.get("monthly_champions") or []) if isinstance(item, dict)]

        results = list(day_aggregate.get("results") or [])
        if results:
            champion = min(
                results,
                key=lambda item: (-float(item.get("points") or 0.0), str(item.get("username") or "")),
            )
            daily_entry = {
                "day": int(day_number),
                "username": str(champion.get("username") or ""),
                "points": round(float(champion.get("points") or 0.0), 2),
                "timestamp": str(day_aggregate.get("timestamp") or ""),
                "avatar": self._copy_hall_avatar(str(champion.get("username") or ""), changed_api_paths),
            }
            daily_champions = [entry for entry in daily_champions if int(entry.get("day") or 0) != int(day_number)]
            daily_champions.append(daily_entry)
            daily_champions.sort(key=lambda item: int(item.get("day") or 0), reverse=True)

        leaderboards_dir = self.api_dir / "leaderboards"
        for month_key in touched_months:
            month_path = leaderboards_dir / f"{month_key}.json"
            month_payload = _load_json(month_path, {})
            leaderboard = list(month_payload.get("leaderboard") or [])
            if not leaderboard:
                continue
            top = leaderboard[0]
            monthly_entry = {
                "month": month_key,
                "username": str(top.get("u") or ""),
                "points": round(float(top.get("p") or 0.0), 2),
                "avatar": self._copy_hall_avatar(str(top.get("u") or ""), changed_api_paths),
            }
            monthly_champions = [entry for entry in monthly_champions if str(entry.get("month") or "") != month_key]
            monthly_champions.append(monthly_entry)
            monthly_champions.sort(key=lambda item: str(item.get("month") or ""), reverse=True)

        output = {
            "last_updated": datetime.now().isoformat(),
            "daily_champions": daily_champions,
            "monthly_champions": monthly_champions,
        }
        if _write_json_if_changed(path, output):
            changed_api_paths.add(_to_api_relative(path, self.api_dir))

    def _refresh_club_member_stats(self, changed_api_paths: set[str]) -> None:
        script_path = self.repo_root / "build_club_member_stats.py"
        if not script_path.exists():
            return
        output_path = self.api_dir / "club_members_stats.json"
        before = output_path.read_bytes() if output_path.exists() else b""
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"build_club_member_stats.py failed: {stderr or completed.returncode}")
        after = output_path.read_bytes() if output_path.exists() else b""
        if before != after:
            changed_api_paths.add(_to_api_relative(output_path, self.api_dir))

    def sync_day(
        self,
        day_number: int,
        *,
        publish_to_r2: bool | None = None,
        refresh_club_member_stats: bool = True,
    ) -> WebsiteSyncResult:
        publish_enabled = bool(
            getattr(config, "WEBSITE_SYNC_PUBLISH_TO_R2", True)
            and getattr(config, "AUTO_PUSH_SYNC_R2_FROM_LOCAL", False)
        )
        if publish_to_r2 is not None:
            publish_enabled = bool(publish_to_r2)

        state = self.load_sync_state()
        changed_api_paths: set[str] = set()
        output_lines: list[str] = []

        try:
            canonical_entries = self._load_day_entries(day_number)
            if not canonical_entries:
                raise RuntimeError(f"No canonical event-day entries found for Day {day_number}")

            day_summaries: list[dict[str, Any]] = []
            scoring_games_for_aggregate: list[dict[str, Any]] = []
            type_updates: dict[str, list[dict[str, Any]]] = defaultdict(list)
            unique_day_participants: set[str] = set()
            scoring_ops_by_letter: dict[str, dict[str, list[tuple[int, float, float, int, int, float, str, str]]]] = defaultdict(
                lambda: defaultdict(list)
            )
            history_ops_by_letter: dict[str, dict[str, list[tuple[str, str, int, str, int, int, int]]]] = defaultdict(
                lambda: defaultdict(list)
            )
            monthly_all_deltas: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(_month_bucket))
            monthly_type_deltas: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(
                lambda: defaultdict(lambda: defaultdict(_month_bucket))
            )

            history_index_path = self.api_dir / "player_history" / "index.json"
            existing_history_index = _load_json(history_index_path, {})
            existing_game_ids = {
                str(meta[0])
                for meta in (existing_history_index.get("games") or [])
                if isinstance(meta, list) and meta and str(meta[0]).strip()
            }
            new_game_ids: set[str] = set()
            new_scoring_games_count = 0
            points_scale = int(existing_history_index.get("points_scale") or DEFAULT_POINTS_SCALE)

            games_dir = self.api_dir / "games"
            games_dir.mkdir(parents=True, exist_ok=True)

            for entry in canonical_entries:
                game_id = str(entry.get("game_id") or "")
                game_type = str(entry.get("game_type") or "")
                source = self.events_games_dir / f"{game_id}.json"
                payload = _load_json(source, {})
                if not isinstance(payload, dict) or str(payload.get("game_id") or "") != game_id:
                    raise RuntimeError(f"Missing or invalid event game cache for {game_id}")

                payload_game_type = str(payload.get("game_type") or game_type or "").strip().lower()
                if is_noncanonical_record_game_type(payload_game_type):
                    continue

                full_dest = games_dir / f"{game_id}.json"
                if _copy_file_if_changed(source, full_dest):
                    changed_api_paths.add(_to_api_relative(full_dest, self.api_dir))

                preview_dest = games_dir / f"{game_id}_top.json"
                if _write_json_if_changed(preview_dest, self._build_game_preview(payload)):
                    changed_api_paths.add(_to_api_relative(preview_dest, self.api_dir))

                summary = {
                    "game_id": game_id,
                    "game_type": payload_game_type,
                    "game_display_name": payload.get("game_display_name"),
                    "timestamp": str(payload.get("timestamp") or ""),
                    "total_participants": int(payload.get("total_participants") or len(payload.get("results") or [])),
                    "day_number": int(payload.get("day_number") or day_number),
                    "non_scoring": bool(payload.get("non_scoring", False)),
                }
                day_summaries.append(summary)
                type_updates[payload_game_type].append(summary)

                is_scoring = not bool(payload.get("non_scoring", False)) and payload_game_type not in self.non_scoring_types
                if is_scoring:
                    scoring_games_for_aggregate.append(payload)

                if game_id in existing_game_ids:
                    continue

                new_game_ids.add(game_id)
                if is_scoring:
                    new_scoring_games_count += 1
                    month_key = str(payload.get("timestamp") or "")[:7]

                total_participants = int(payload.get("total_participants") or len(payload.get("results") or []))
                for result in payload.get("results") or []:
                    username = str(result.get("username") or "").strip()
                    if not username:
                        continue
                    unique_day_participants.add(username)
                    letter = _normalize_letter(username)
                    placement = int(result.get("placement") or result.get("rank") or 0)
                    kills = int(result.get("kills") or 0)
                    history_ops_by_letter[letter][username].append(
                        (
                            game_id,
                            payload_game_type,
                            int(payload.get("day_number") or day_number),
                            str(payload.get("timestamp") or ""),
                            placement,
                            int(round(float(result.get("points") or 0.0) * points_scale)),
                            kills,
                        )
                    )

                    if not is_scoring:
                        continue

                    points = float(result.get("points") or 0.0)
                    survival_time = float(result.get("survival_time") or 0.0)
                    damage = float(result.get("damage", result.get("damage_dealt", 0.0)) or 0.0)
                    scoring_ops_by_letter[letter][username].append(
                        (
                            placement,
                            points,
                            survival_time,
                            total_participants,
                            kills,
                            damage,
                            payload_game_type,
                            game_id,
                        )
                    )

                    month_bucket = monthly_all_deltas[month_key][username]
                    month_bucket["points"] += points
                    month_bucket["games"] += 1
                    month_bucket["wins"] += 1 if placement == 1 else 0
                    month_bucket["best_placement"] = min(month_bucket["best_placement"], placement or float("inf"))
                    month_bucket["total_kills"] += kills
                    month_bucket["total_placement"] += placement

                    typed_bucket = monthly_type_deltas[month_key][payload_game_type][username]
                    typed_bucket["points"] += points
                    typed_bucket["games"] += 1
                    typed_bucket["wins"] += 1 if placement == 1 else 0
                    typed_bucket["best_placement"] = min(typed_bucket["best_placement"], placement or float("inf"))
                    typed_bucket["total_kills"] += kills
                    typed_bucket["total_placement"] += placement

            day_summaries.sort(key=lambda item: (str(item.get("timestamp") or ""), str(item.get("game_id") or "")))
            day_summary_payload, day_meta = self._build_day_summary(
                day_number,
                day_summaries,
                len(unique_day_participants),
            )
            days_dir = self.api_dir / "days"
            days_dir.mkdir(parents=True, exist_ok=True)
            day_path = days_dir / f"{int(day_number)}.json"
            if _write_json_if_changed(day_path, day_summary_payload):
                changed_api_paths.add(_to_api_relative(day_path, self.api_dir))

            aggregate_payload, aggregate_preview = self._build_day_aggregate(day_number, scoring_games_for_aggregate)
            aggregate_path = days_dir / f"{int(day_number)}_aggregate.json"
            if _write_json_if_changed(aggregate_path, aggregate_payload):
                changed_api_paths.add(_to_api_relative(aggregate_path, self.api_dir))
            if aggregate_preview is not None:
                aggregate_preview_path = days_dir / f"{int(day_number)}_aggregate_top.json"
                if _write_json_if_changed(aggregate_preview_path, aggregate_preview):
                    changed_api_paths.add(_to_api_relative(aggregate_preview_path, self.api_dir))

            type_counts = self._update_type_indexes(type_updates, changed_api_paths)
            self._update_player_history(canonical_entries, history_ops_by_letter, new_game_ids, changed_api_paths)
            self._update_player_stats(scoring_ops_by_letter, new_scoring_games_count, changed_api_paths)
            touched_months = self._update_monthly_leaderboards(
                monthly_all_deltas,
                monthly_type_deltas,
                changed_api_paths,
            )
            platforms_metadata, platform_changed_paths = export_platform_partitions(
                self.api_dir,
                self._load_all_event_games(),
                repo_root=self.repo_root,
                avatar_cache_dir=self.avatar_cache_dir,
                preview_limit=self.preview_limit,
                total_followers=self._count_followers(),
            )
            for path in platform_changed_paths:
                try:
                    changed_api_paths.add(_to_api_relative(path, self.api_dir))
                except Exception:
                    continue
            self._refresh_index(day_meta, type_counts, touched_months, changed_api_paths, platforms_metadata)
            self._refresh_media_kit(changed_api_paths)
            self._refresh_hall_of_fame(day_number, aggregate_payload, touched_months, changed_api_paths)
            if refresh_club_member_stats:
                self._refresh_club_member_stats(changed_api_paths)

            publish_result = cloud_sync.SyncResult(False, "skipped", "R2 publish disabled by config")
            if publish_enabled and changed_api_paths:
                publish_result = cloud_sync.push_api_files(sorted(changed_api_paths), api_dir=self.api_dir)
            elif publish_enabled:
                publish_result = cloud_sync.SyncResult(True, "success", "No changed API files to publish.")

            state["last_day_synced"] = max(int(state.get("last_day_synced") or 0), int(day_number))
            days_synced = {
                int(value)
                for value in list(state.get("days_synced") or [])
                if str(value).strip()
            }
            days_synced.add(int(day_number))
            state["days_synced"] = sorted(days_synced)
            state["last_run_at"] = datetime.now().isoformat()
            state["last_error"] = ""
            if publish_result.ok:
                state["last_published_at"] = datetime.now().isoformat()
            self._save_sync_state(state)

            output_lines.append(
                f"Website day sync complete for Day {day_number}: {len(changed_api_paths)} changed API file(s), "
                f"{len(new_game_ids)} new canonical game(s)."
            )
            if publish_result.message:
                output_lines.append(publish_result.message)

            return WebsiteSyncResult(
                day_number=int(day_number),
                ok=True,
                changed_api_paths=sorted(changed_api_paths),
                changed_count=len(changed_api_paths),
                published=bool(publish_result.ok),
                publish_message=publish_result.message,
                new_game_ids=sorted(new_game_ids),
                output_excerpt="\n".join(output_lines[-10:]),
            )
        except Exception as exc:
            state["last_run_at"] = datetime.now().isoformat()
            state["last_error"] = str(exc)
            self._save_sync_state(state)
            raise


def load_website_sync_state(path: Path | None = None) -> dict[str, Any]:
    return WebsiteDeltaSync(sync_state_path=path).load_sync_state()
