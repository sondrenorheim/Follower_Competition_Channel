"""Helpers for mapping Facebook video/post ids to game/day metadata safely."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _normalize_id(value: Any) -> str:
    return str(value or "").strip()


def _video_key(video_id: str | None) -> str | None:
    v = _normalize_id(video_id)
    return f"video:{v}" if v else None


def _post_keys(post_id: str | None) -> list[str]:
    raw = _normalize_id(post_id)
    if not raw:
        return []
    keys = [f"post:{raw}"]
    if "_" in raw:
        suffix = raw.split("_", 1)[1].strip()
        if suffix:
            keys.append(f"post:{suffix}")
    seen = set()
    deduped = []
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def _acquire_lock(lock_path: Path, timeout_seconds: float = 10.0, stale_seconds: float = 120.0):
    start = time.time()
    pid = os.getpid()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{pid}|{int(time.time())}".encode("utf-8", errors="ignore"))
            return fd
        except FileExistsError:
            if (time.time() - start) > timeout_seconds:
                raise TimeoutError(f"Timed out acquiring lock: {lock_path}")
            try:
                mtime = lock_path.stat().st_mtime
                if (time.time() - mtime) > stale_seconds:
                    lock_path.unlink(missing_ok=True)
                    continue
            except Exception:
                pass
            time.sleep(0.05)


def _release_lock(lock_path: Path, fd) -> None:
    try:
        os.close(fd)
    except Exception:
        pass
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


def _load_map(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        pass
    return {}


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def lookup_mapping(map_path: Path, video_id: str | None = None, post_id: str | None = None) -> dict | None:
    """Lookup mapping by video id or post id keys."""
    path = Path(map_path)
    data = _load_map(path)
    vkey = _video_key(video_id)
    if vkey and vkey in data:
        return data[vkey]
    for pkey in _post_keys(post_id):
        if pkey in data:
            return data[pkey]
    return None


def remember_mapping(
    map_path: Path,
    *,
    video_id: str | None,
    post_id: str | None,
    game_type: str,
    day_number: int,
    source: str = "manual",
    extra: dict[str, Any] | None = None,
    max_entries: int = 5000,
) -> dict[str, Any]:
    """Persist mapping for facebook video/post identifiers."""
    if not game_type:
        raise ValueError("game_type is required")
    day_value = int(day_number)
    now_ts = int(time.time())
    entry = {
        "game_type": str(game_type),
        "day_number": day_value,
        "source": str(source or "manual"),
        "updated_at": now_ts,
    }
    if isinstance(extra, dict):
        for key, value in extra.items():
            if value is None:
                continue
            entry[str(key)] = value

    path = Path(map_path)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_fd = _acquire_lock(lock_path)
    try:
        data = _load_map(path)
        keys = []
        vkey = _video_key(video_id)
        if vkey:
            keys.append(vkey)
        keys.extend(_post_keys(post_id))
        for key in keys:
            data[key] = dict(entry)

        if max_entries > 0 and len(data) > max_entries:
            sorted_items = sorted(
                data.items(),
                key=lambda kv: int(kv[1].get("updated_at", 0)),
                reverse=True,
            )
            data = dict(sorted_items[:max_entries])

        _atomic_write_json(path, data)
        return {
            "ok": True,
            "keys": keys,
            "entry": entry,
            "size": len(data),
        }
    finally:
        _release_lock(lock_path, lock_fd)
