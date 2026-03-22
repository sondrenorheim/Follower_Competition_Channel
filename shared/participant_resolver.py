from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import config

from .api import InstagramAPI
from .platform_targets import get_requested_participant_count, normalize_platform_target


def _normalize_username(value: Any) -> str:
    return str(value or "").strip().lstrip("@").lower()


def _entry_identity(entry: dict) -> tuple[str, str]:
    username = _normalize_username(entry.get("username"))
    if username:
        return ("username", username)

    for key in ("youtube_channel_id", "facebook_user_id", "id", "profile_url"):
        value = str(entry.get(key) or "").strip()
        if value:
            return (key, value)

    return ("fallback", repr(sorted(entry.items())))


def _dedupe_entries(entries: list[dict], seen: set[tuple[str, str]] | None = None) -> list[dict]:
    deduped: list[dict] = []
    identity_set = seen if seen is not None else set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identity = _entry_identity(entry)
        if identity in identity_set:
            continue
        identity_set.add(identity)
        deduped.append(dict(entry))
    return deduped


def _resolve_import_path(path_value: str | Path | None) -> Path | None:
    text = str(path_value or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = Path(config.PROJECT_ROOT) / path
    return path.resolve()


def _get_mode_import_file(game_mode: str) -> str:
    overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {})
    normalized_mode = str(game_mode or "").strip().lower()
    if isinstance(overrides, dict):
        override = overrides.get(normalized_mode)
        if override:
            return str(override)
    return str(getattr(config, "FOLLOWER_IMPORT_FILE", "") or "")


def _load_from_import_file(import_file: str | Path | None, count: int | None = None) -> list[dict]:
    path = _resolve_import_path(import_file)
    if path is None or not path.exists():
        return []
    api = InstagramAPI()
    try:
        followers = api._import_from_file(str(path), count) or []
    except Exception as exc:
        print(f"[WARN] Failed to import participants from {path}: {exc}")
        return []
    return [dict(entry) for entry in followers if isinstance(entry, dict)]


def _sample_entries(entries: list[dict], desired_count: int | None, seed_token: str) -> list[dict]:
    if desired_count is None or desired_count <= 0 or len(entries) <= desired_count:
        return [dict(entry) for entry in entries]
    rng = random.Random(seed_token)
    indices = list(range(len(entries)))
    rng.shuffle(indices)
    chosen = sorted(indices[:desired_count])
    return [dict(entries[index]) for index in chosen]


def resolve_participants(
    game_mode: str,
    *,
    platform_target: str | None = None,
    explicit_count: int | None = None,
) -> dict[str, Any]:
    normalized_platform = normalize_platform_target(platform_target)
    requested_count = get_requested_participant_count(
        explicit_count=explicit_count,
        platform_target=normalized_platform,
    )

    if bool(getattr(config, "TEST_MINIMAL_PLAYERS", False)):
        test_count = int(getattr(config, "TEST_MINIMAL_PLAYER_COUNT", 100) or 100)
        if requested_count is not None and requested_count > 0:
            test_count = min(test_count, requested_count)
        api = InstagramAPI()
        participants = api.fetch_followers(test_count)
        return {
            "participants": [dict(entry) for entry in participants],
            "requested_count": test_count,
            "youtube_count": 0,
            "instagram_top_up_count": test_count,
            "used_fallback": normalized_platform == "youtube",
            "platform_target": normalized_platform,
        }

    if normalized_platform != "youtube":
        api = InstagramAPI()
        participants = api.fetch_followers(requested_count)
        actual_count = len(participants)
        return {
            "participants": [dict(entry) for entry in participants],
            "requested_count": requested_count if requested_count is not None else actual_count,
            "youtube_count": 0,
            "instagram_top_up_count": actual_count,
            "used_fallback": False,
            "platform_target": normalized_platform,
        }

    youtube_import_file = getattr(config, "YOUTUBE_PARTICIPANT_FILE", "Followers/youtube_join_participants.json")
    instagram_import_file = getattr(config, "YOUTUBE_TOP_UP_IMPORT_FILE", "") or _get_mode_import_file(game_mode)
    top_up_enabled = bool(getattr(config, "YOUTUBE_TOP_UP_WITH_INSTAGRAM", True))

    youtube_entries = _dedupe_entries(_load_from_import_file(youtube_import_file, count=None))
    requested_total = requested_count if requested_count is not None else len(youtube_entries)
    if requested_total <= 0:
        requested_total = int(getattr(config, "YOUTUBE_DEFAULT_PARTICIPANT_COUNT", 1000) or 1000)

    seed_base = f"{getattr(config, 'DAY_NUMBER', 1)}:{game_mode}:{normalized_platform}"
    selected_youtube = _sample_entries(youtube_entries, requested_total, f"{seed_base}:youtube")

    combined: list[dict] = []
    seen: set[tuple[str, str]] = set()
    combined.extend(_dedupe_entries(selected_youtube, seen))

    instagram_top_up_count = 0
    used_fallback = False
    if len(combined) < requested_total and top_up_enabled:
        used_fallback = True
        remaining = requested_total - len(combined)
        instagram_entries = _dedupe_entries(_load_from_import_file(instagram_import_file, count=None))
        instagram_entries = _dedupe_entries(instagram_entries, seen)
        selected_instagram = _sample_entries(instagram_entries, remaining, f"{seed_base}:instagram")
        instagram_top_up_count = len(selected_instagram)
        combined.extend(selected_instagram)

    if len(combined) < requested_total:
        requested_total = len(combined)

    youtube_count = min(len(selected_youtube), len(combined))
    print(
        "[INFO] Participant resolver:"
        f" platform={normalized_platform}"
        f" mode={game_mode}"
        f" requested={requested_total}"
        f" youtube={youtube_count}"
        f" instagram_top_up={instagram_top_up_count}"
        f" fallback={'yes' if used_fallback else 'no'}"
    )
    return {
        "participants": combined,
        "requested_count": requested_total,
        "youtube_count": youtube_count,
        "instagram_top_up_count": instagram_top_up_count,
        "used_fallback": used_fallback,
        "platform_target": normalized_platform,
    }
