"""Helpers for storing YouTube JOIN commenters in follower JSON files safely."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_YT_ID_TO_USERNAME_CACHE: dict[str, str] | None = None
_YT_ID_CACHE_MTIME: float | None = None
_YT_ID_CACHE_PATH: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_username(value: Any) -> str:
    return str(value or "").strip().lower()


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


def _load_followers(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Follower store must be a JSON list: {path}")
    return [entry for entry in data if isinstance(entry, dict)]


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _invalidate_youtube_id_cache() -> None:
    global _YT_ID_TO_USERNAME_CACHE, _YT_ID_CACHE_MTIME, _YT_ID_CACHE_PATH
    _YT_ID_TO_USERNAME_CACHE = None
    _YT_ID_CACHE_MTIME = None
    _YT_ID_CACHE_PATH = None


def _load_youtube_id_cache(path: Path) -> dict[str, str]:
    global _YT_ID_TO_USERNAME_CACHE, _YT_ID_CACHE_MTIME, _YT_ID_CACHE_PATH
    try:
        mtime = path.stat().st_mtime
    except Exception:
        _invalidate_youtube_id_cache()
        return {}

    cache_key = str(path.resolve())
    if (
        _YT_ID_TO_USERNAME_CACHE is not None
        and _YT_ID_CACHE_MTIME == mtime
        and _YT_ID_CACHE_PATH == cache_key
    ):
        return _YT_ID_TO_USERNAME_CACHE

    mapping: dict[str, str] = {}
    try:
        followers = _load_followers(path)
    except Exception:
        _invalidate_youtube_id_cache()
        return {}
    for entry in followers:
        channel_id = str(entry.get("youtube_channel_id", "")).strip()
        if not channel_id or channel_id in mapping:
            continue
        username = str(entry.get("username", "")).strip()
        if username:
            mapping[channel_id] = username

    _YT_ID_TO_USERNAME_CACHE = mapping
    _YT_ID_CACHE_MTIME = mtime
    _YT_ID_CACHE_PATH = cache_key
    return mapping


def lookup_username_by_youtube_channel_id(follower_file: Path, youtube_channel_id: str | None) -> str | None:
    """Return mapped in-game username for a YouTube channel id, if present."""
    channel_id = str(youtube_channel_id or "").strip()
    if not channel_id:
        return None
    mapping = _load_youtube_id_cache(Path(follower_file))
    return mapping.get(channel_id)


def upsert_youtube_join(
    follower_file: Path,
    youtube_channel_id: str | None,
    youtube_display_name: str | None,
    comment_id: str | None,
    video_id: str | None,
    joined_at: str | None = None,
) -> dict[str, Any]:
    """
    Upsert a YouTube JOIN commenter into follower JSON.

    Dedupe order:
    1) youtube_channel_id
    2) case-insensitive username match
    """
    follower_path = Path(follower_file)
    lock_path = follower_path.with_suffix(follower_path.suffix + ".lock")
    lock_fd = _acquire_lock(lock_path)
    try:
        followers = _load_followers(follower_path)
        channel_id = str(youtube_channel_id or "").strip()
        display_name = str(youtube_display_name or "").strip()
        if not display_name and channel_id:
            display_name = f"yt_{channel_id}"
        if not display_name:
            display_name = "YouTubeUser"

        joined_ts = str(joined_at or _utc_now_iso())
        username_norm = _normalize_username(display_name)

        match_index = None
        match_reason = "created"

        if channel_id:
            for idx, entry in enumerate(followers):
                if str(entry.get("youtube_channel_id", "")).strip() == channel_id:
                    match_index = idx
                    match_reason = "updated_by_youtube_channel_id"
                    break

        if match_index is None and username_norm:
            for idx, entry in enumerate(followers):
                if _normalize_username(entry.get("username")) == username_norm:
                    match_index = idx
                    match_reason = "updated_by_username"
                    break

        profile_url = f"https://www.youtube.com/channel/{channel_id}" if channel_id else ""
        payload_fields = {
            "username": display_name,
            "profile_url": profile_url,
            "profile_pic_url": "",
            "source_platform": "youtube",
            "source_origin": "youtube_comment_join",
            "youtube_channel_id": channel_id,
            "youtube_display_name": display_name,
            "youtube_joined_at": joined_ts,
            "youtube_join_comment_id": str(comment_id or ""),
            "youtube_join_video_id": str(video_id or ""),
        }

        if match_index is None:
            followers.append(payload_fields)
            status = "created"
        else:
            entry = followers[match_index]
            if not str(entry.get("profile_pic_url", "")).strip():
                entry["profile_pic_url"] = payload_fields["profile_pic_url"]
            if not str(entry.get("profile_url", "")).strip() and profile_url:
                entry["profile_url"] = profile_url
            for key, value in payload_fields.items():
                if key == "profile_pic_url":
                    continue
                entry[key] = value
            status = match_reason

        followers.sort(key=lambda item: _normalize_username(item.get("username")))
        _atomic_write_json(follower_path, followers)
        _invalidate_youtube_id_cache()
        return {
            "ok": True,
            "status": status,
            "username": display_name,
            "youtube_channel_id": channel_id,
            "total_followers": len(followers),
        }
    finally:
        _release_lock(lock_path, lock_fd)
