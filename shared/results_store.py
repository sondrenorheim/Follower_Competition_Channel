"""
Local storage safety helpers for game results and statistics.

This module provides:
- atomic JSON writes
- append-only game event backups
- full snapshot backups
- best-source loading for recovery
- integrity/recovery logging
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = REPO_ROOT / "backups" / "game_results"
EVENTS_ROOT = BACKUP_ROOT / "events"
EVENT_GAMES_ROOT = EVENTS_ROOT / "games"
EVENT_DAYS_ROOT = EVENTS_ROOT / "days"
SNAPSHOTS_ROOT = BACKUP_ROOT / "snapshots"
MANIFESTS_ROOT = BACKUP_ROOT / "manifests"
EVENTS_INDEX_PATH = MANIFESTS_ROOT / "events_index.jsonl"
SNAPSHOTS_INDEX_PATH = MANIFESTS_ROOT / "snapshots_index.jsonl"
RECOVERY_LOG_PATH = REPO_ROOT / "logs" / "results_integrity" / "recovery.log"


def _ensure_store_dirs() -> None:
    EVENTS_ROOT.mkdir(parents=True, exist_ok=True)
    EVENT_GAMES_ROOT.mkdir(parents=True, exist_ok=True)
    EVENT_DAYS_ROOT.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFESTS_ROOT.mkdir(parents=True, exist_ok=True)
    RECOVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _to_repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _to_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return str(path)


def _sanitize_reason(reason: str) -> str:
    cleaned = []
    for char in str(reason or "snapshot"):
        if char.isalnum() or char in ("-", "_"):
            cleaned.append(char)
        else:
            cleaned.append("_")
    value = "".join(cleaned).strip("_")
    return value or "snapshot"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _results_count(game: dict[str, Any]) -> int:
    results = game.get("results")
    if isinstance(results, list):
        return len(results)
    return 0


def _game_timestamp(game: dict[str, Any]) -> str:
    value = game.get("timestamp", "")
    return value if isinstance(value, str) else ""


def choose_preferred_game(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Keep the most complete game payload:
    1) larger results array
    2) newest timestamp (tie-break)
    """
    if not existing:
        return candidate
    if not candidate:
        return existing

    existing_results = _results_count(existing)
    candidate_results = _results_count(candidate)
    if candidate_results > existing_results:
        return candidate
    if candidate_results < existing_results:
        return existing

    if _game_timestamp(candidate) > _game_timestamp(existing):
        return candidate
    return existing


def merge_games(*game_lists: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for games in game_lists:
        for game in games or []:
            if not isinstance(game, dict):
                continue
            game_id = game.get("game_id")
            if not isinstance(game_id, str) or not game_id:
                continue
            existing = merged.get(game_id)
            merged[game_id] = choose_preferred_game(existing or {}, game)

    return sorted(
        merged.values(),
        key=lambda g: (str(g.get("timestamp", "")), str(g.get("game_id", ""))),
    )


def _is_valid_game_history(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    games = payload.get("games")
    if not isinstance(games, list):
        return False
    return True


def _game_count(payload: Any) -> int:
    if not _is_valid_game_history(payload):
        return 0
    ids = {
        game.get("game_id")
        for game in payload.get("games", [])
        if isinstance(game, dict) and isinstance(game.get("game_id"), str) and game.get("game_id")
    }
    return len(ids)


def _is_valid_player_stats(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if "players" in payload:
        return isinstance(payload.get("players"), dict)
    return True


def _player_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    if isinstance(payload.get("players"), dict):
        return len(payload.get("players", {}))

    metadata_keys = {"last_updated", "total_games_recorded", "game_highscores"}
    keys = [k for k in payload.keys() if k not in metadata_keys]
    if not keys:
        return 0
    # Legacy format: top-level username -> stats payload.
    likely_players = 0
    for key in keys[:100]:
        value = payload.get(key)
        if isinstance(value, (list, dict)):
            likely_players += 1
    if likely_players == 0:
        return 0
    return len(keys)


def atomic_write_json(path: str | Path, payload: Any, *, retries: int = 5, retry_delay_s: float = 0.25) -> None:
    """
    Atomically write JSON to disk using a temp file in the same directory.
    """
    target = _to_repo_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max(1, retries) + 1):
        tmp_path = target.parent / f".{target.name}.tmp.{os.getpid()}.{time.time_ns()}"
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
            return
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            if attempt >= retries:
                raise
            time.sleep(max(0.0, retry_delay_s) * attempt)


def sha256_file(path: str | Path) -> str:
    file_path = _to_repo_path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_recovery_log(event: dict[str, Any]) -> None:
    _ensure_store_dirs()
    payload = dict(event or {})
    payload.setdefault("timestamp", datetime.now().isoformat())
    _append_jsonl(RECOVERY_LOG_PATH, payload)


def append_game_event(game_record: dict[str, Any]) -> Path | None:
    """
    Append a single game record to the daily NDJSON event log.
    """
    if not isinstance(game_record, dict):
        return None
    game_id = game_record.get("game_id")
    if not isinstance(game_id, str) or not game_id:
        return None

    _ensure_store_dirs()

    timestamp = game_record.get("timestamp")
    if isinstance(timestamp, str) and len(timestamp) >= 10 and timestamp[4] == "-" and timestamp[7] == "-":
        day = timestamp[:10]
    else:
        day = datetime.now().strftime("%Y-%m-%d")
        timestamp = timestamp if isinstance(timestamp, str) else datetime.now().isoformat()

    year = day[:4]
    month = day[5:7]
    event_file = EVENTS_ROOT / year / month / f"{day}.ndjson"
    event_file.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(game_record, ensure_ascii=False, separators=(",", ":"))
    encoded_line = f"{line}\n".encode("utf-8")
    with event_file.open("ab") as f:
        f.write(encoded_line)
        f.flush()
        os.fsync(f.fileno())

    manifest_entry = {
        "timestamp": datetime.now().isoformat(),
        "game_id": game_id,
        "game_timestamp": timestamp,
        "event_file": _to_rel(event_file),
        "line_sha256": hashlib.sha256(encoded_line.rstrip(b"\n")).hexdigest(),
        "line_size": len(encoded_line),
    }
    _append_jsonl(EVENTS_INDEX_PATH, manifest_entry)
    _write_event_game_cache(game_record)
    _update_event_day_summary(game_record)
    return event_file


def _write_event_game_cache(game_record: dict[str, Any]) -> Path | None:
    game_id = str(game_record.get("game_id") or "").strip()
    if not game_id:
        return None
    target = EVENT_GAMES_ROOT / f"{game_id}.json"
    atomic_write_json(target, game_record)
    return target


def _build_day_summary_entry(game_record: dict[str, Any]) -> dict[str, Any] | None:
    game_id = str(game_record.get("game_id") or "").strip()
    game_type = str(game_record.get("game_type") or "").strip()
    if not game_id or not game_type:
        return None
    total_participants = game_record.get("total_participants")
    if total_participants in (None, ""):
        results = game_record.get("results")
        if isinstance(results, list):
            total_participants = len(results)
    entry = {
        "game_id": game_id,
        "game_type": game_type,
        "game_display_name": game_record.get("game_display_name"),
        "timestamp": game_record.get("timestamp"),
        "total_participants": total_participants,
        "non_scoring": bool(game_record.get("non_scoring", False)),
    }
    return entry


def _update_event_day_summary(game_record: dict[str, Any]) -> Path | None:
    day_number = game_record.get("day_number")
    try:
        day_value = int(day_number)
    except Exception:
        return None

    entry = _build_day_summary_entry(game_record)
    if entry is None:
        return None

    target = EVENT_DAYS_ROOT / f"{day_value}.json"
    existing = _load_json(target)
    if not isinstance(existing, dict):
        existing = {
            "day_number": day_value,
            "total_games": 0,
            "games": [],
        }

    games = []
    seen_game_ids = set()
    replaced = False
    for payload in list(existing.get("games") or []):
        if not isinstance(payload, dict):
            continue
        existing_game_id = str(payload.get("game_id") or "").strip()
        if not existing_game_id or existing_game_id in seen_game_ids:
            continue
        if existing_game_id == entry["game_id"]:
            games.append(entry)
            replaced = True
        else:
            games.append(payload)
        seen_game_ids.add(existing_game_id)

    if not replaced:
        games.append(entry)

    games.sort(key=lambda item: (str(item.get("timestamp") or ""), str(item.get("game_id") or "")))
    summary = {
        "day_number": day_value,
        "total_games": len(games),
        "games": games,
    }
    atomic_write_json(target, summary)
    return target


def _snapshot_file_candidates(filename: str) -> list[Path]:
    if not SNAPSHOTS_ROOT.exists():
        return []
    files = []
    for directory in SNAPSHOTS_ROOT.iterdir():
        if not directory.is_dir():
            continue
        candidate = directory / filename
        if candidate.exists():
            files.append(candidate)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _load_games_from_api() -> dict[str, Any]:
    games_dir = REPO_ROOT / "website" / "public" / "api" / "games"
    if not games_dir.exists():
        return {"games": []}

    games = []
    for path in sorted(games_dir.glob("*.json")):
        if path.name.endswith("_top.json"):
            continue
        payload = _load_json(path)
        if isinstance(payload, dict) and payload.get("game_id"):
            games.append(payload)

    return {"games": merge_games(games)}


def count_api_games() -> int:
    games_dir = REPO_ROOT / "website" / "public" / "api" / "games"
    if not games_dir.exists():
        return 0
    return sum(1 for path in games_dir.glob("*.json") if not path.name.endswith("_top.json"))


def load_games_from_events() -> dict[str, Any]:
    if not EVENTS_ROOT.exists():
        return {"games": []}

    games = []
    for path in sorted(EVENTS_ROOT.rglob("*.ndjson")):
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        continue
                    if isinstance(payload, dict) and payload.get("game_id"):
                        games.append(payload)
        except Exception:
            continue

    return {"games": merge_games(games)}


def create_snapshot(reason: str, files: Iterable[str | Path]) -> Path:
    """
    Create a full-file snapshot under backups/game_results/snapshots/.
    """
    _ensure_store_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_reason = _sanitize_reason(reason)
    snapshot_dir = SNAPSHOTS_ROOT / f"{stamp}_{safe_reason}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    metadata: dict[str, Any] = {
        "snapshot": snapshot_dir.name,
        "created_at": datetime.now().isoformat(),
        "reason": safe_reason,
        "files": [],
    }

    for file_value in files:
        source_path = _to_repo_path(file_value)
        entry: dict[str, Any] = {
            "source": _to_rel(source_path),
            "source_absolute": str(source_path),
            "exists": source_path.exists(),
        }
        if not source_path.exists():
            metadata["files"].append(entry)
            continue

        destination = snapshot_dir / source_path.name
        shutil.copy2(source_path, destination)
        entry["snapshot_file"] = destination.name
        entry["snapshot_path"] = _to_rel(destination)
        entry["size"] = destination.stat().st_size
        entry["sha256"] = sha256_file(destination)

        payload = _load_json(destination)
        if source_path.name == "game_history.json":
            entry["game_count"] = _game_count(payload)
        elif source_path.name == "player_statistics.json":
            entry["player_count"] = _player_count(payload)

        metadata["files"].append(entry)

    metadata_path = snapshot_dir / "metadata.json"
    atomic_write_json(metadata_path, metadata)

    index_entry = {
        "timestamp": metadata["created_at"],
        "snapshot": snapshot_dir.name,
        "reason": safe_reason,
        "path": _to_rel(snapshot_dir),
        "files": [
            {
                "source": item.get("source"),
                "snapshot_file": item.get("snapshot_file"),
                "size": item.get("size", 0),
                "sha256": item.get("sha256"),
                "game_count": item.get("game_count"),
                "player_count": item.get("player_count"),
            }
            for item in metadata["files"]
            if item.get("exists")
        ],
    }
    _append_jsonl(SNAPSHOTS_INDEX_PATH, index_entry)
    return snapshot_dir


def _pick_best_candidate(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    if not candidates:
        return {}, ""
    best = max(candidates, key=lambda c: (int(c.get("score", 0)), float(c.get("mtime", 0.0))))
    return best.get("payload", {}), best.get("source", "")


def load_best_game_history(preferred: str = "game_history.json", deep_scan: bool = False) -> tuple[dict[str, Any], str]:
    """
    Load the best available game history source.

    Selection preference:
    - highest game count
    - newest mtime as tie-break
    """
    preferred_path = _to_repo_path(preferred)
    preferred_payload = _load_json(preferred_path) if preferred_path.exists() else None
    preferred_count = _game_count(preferred_payload)
    api_file_count = count_api_games()

    if _is_valid_game_history(preferred_payload) and preferred_count > 0 and preferred_count >= api_file_count:
        return preferred_payload, str(preferred_path)

    candidates: list[dict[str, Any]] = []

    def add_candidate(path: Path, payload: Any) -> None:
        count = _game_count(payload)
        if count <= 0:
            return
        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = 0.0
        candidates.append(
            {
                "payload": {"games": merge_games(payload.get("games", []))},
                "source": str(path),
                "score": count,
                "mtime": mtime,
            }
        )

    if _is_valid_game_history(preferred_payload):
        add_candidate(preferred_path, preferred_payload)

    if api_file_count > 0:
        api_payload = _load_games_from_api()
        api_source = _to_repo_path("website/public/api/games")
        if _is_valid_game_history(api_payload):
            add_candidate(api_source, api_payload)

    # Fast-path for runtime calls: rely on API baseline unless deep scan is requested.
    if not deep_scan:
        best_payload, best_source = _pick_best_candidate(candidates)
        if _is_valid_game_history(best_payload):
            return {"games": merge_games(best_payload.get("games", []))}, best_source

    for snapshot_file in _snapshot_file_candidates("game_history.json")[:30]:
        payload = _load_json(snapshot_file)
        if _is_valid_game_history(payload):
            add_candidate(snapshot_file, payload)

    recovered_path = _to_repo_path("game_history_recovered.json")
    if recovered_path.exists():
        payload = _load_json(recovered_path)
        if _is_valid_game_history(payload):
            add_candidate(recovered_path, payload)

    backup_paths = sorted(
        _to_repo_path(".").glob("game_history_backup_*.json"),
        key=lambda p: p.stat().st_size if p.exists() else 0,
        reverse=True,
    )
    for backup_path in backup_paths[:8]:
        payload = _load_json(backup_path)
        if _is_valid_game_history(payload):
            add_candidate(backup_path, payload)

    events_payload = load_games_from_events()
    events_count = _game_count(events_payload)
    if events_count > 0:
        events_source = EVENTS_ROOT
        candidates.append(
            {
                "payload": events_payload,
                "source": str(events_source),
                "score": events_count,
                "mtime": events_source.stat().st_mtime if events_source.exists() else 0.0,
            }
        )

    best_payload, best_source = _pick_best_candidate(candidates)
    if _is_valid_game_history(best_payload):
        return {"games": merge_games(best_payload.get("games", []))}, best_source
    return {"games": []}, ""


def load_best_player_stats(preferred: str = "player_statistics.json") -> tuple[dict[str, Any], str]:
    """
    Load the best available player stats source.
    """
    preferred_path = _to_repo_path(preferred)
    preferred_payload = _load_json(preferred_path) if preferred_path.exists() else None
    preferred_players = _player_count(preferred_payload)
    if _is_valid_player_stats(preferred_payload) and preferred_players > 0:
        return preferred_payload, str(preferred_path)

    candidates: list[dict[str, Any]] = []

    def add_candidate(path: Path, payload: Any) -> None:
        players = _player_count(payload)
        if players <= 0:
            return
        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = 0.0
        candidates.append(
            {
                "payload": payload,
                "source": str(path),
                "score": players,
                "mtime": mtime,
            }
        )

    if _is_valid_player_stats(preferred_payload):
        add_candidate(preferred_path, preferred_payload)

    for snapshot_file in _snapshot_file_candidates("player_statistics.json")[:30]:
        payload = _load_json(snapshot_file)
        if _is_valid_player_stats(payload):
            add_candidate(snapshot_file, payload)

    best_payload, best_source = _pick_best_candidate(candidates)
    if _is_valid_player_stats(best_payload) and _player_count(best_payload) > 0:
        return best_payload, best_source

    # Default empty format.
    fallback = {
        "last_updated": "",
        "total_games_recorded": 0,
        "game_highscores": {},
        "players": {},
    }
    return fallback, ""
