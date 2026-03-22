from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config


def normalize_platform_target(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"youtube", "yt"}:
        return "youtube"
    return "instagram"


def get_platform_target() -> str:
    return normalize_platform_target(getattr(config, "PLATFORM_TARGET", "instagram"))


def get_native_youtube_game_modes() -> set[str]:
    raw = getattr(config, "YOUTUBE_NATIVE_GAME_MODES", ["maze_rush", "flappy_followers"])
    if isinstance(raw, str):
        values = [part.strip().lower() for part in raw.split(",")]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(part).strip().lower() for part in raw]
    else:
        values = []
    return {value for value in values if value}


def is_native_youtube_game(game_mode: str | None, platform_target: str | None = None) -> bool:
    normalized_mode = str(game_mode or "").strip().lower()
    if not normalized_mode:
        return False
    return (
        normalize_platform_target(platform_target) == "youtube"
        and normalized_mode in get_native_youtube_game_modes()
    )


def resolve_record_game_type(game_mode: str, platform_target: str | None = None) -> str:
    normalized_mode = str(game_mode or "").strip().lower()
    if is_native_youtube_game(normalized_mode, platform_target):
        return f"youtube_{normalized_mode}"
    return normalized_mode


def resolve_record_game_display_name(game_mode: str, platform_target: str | None = None) -> str:
    normalized_mode = str(game_mode or "").strip().lower()
    base_name = normalized_mode.replace("_", " ").strip().title() or "Follower Battlegrounds"
    if is_native_youtube_game(normalized_mode, platform_target):
        return f"{base_name} (YouTube)"
    return base_name


def resolve_output_video_path(
    game_mode: str,
    *,
    day_number: int | None = None,
    test_mode: bool | None = None,
    platform_target: str | None = None,
) -> str:
    if is_native_youtube_game(game_mode, platform_target):
        return config.get_youtube_variant_video_path(
            game_mode=game_mode,
            day_number=day_number,
            test_mode=test_mode,
        )
    return config.get_output_video_path(
        game_mode=game_mode,
        day_number=day_number,
        test_mode=test_mode,
    )


def get_requested_participant_count(
    *,
    explicit_count: int | None = None,
    platform_target: str | None = None,
) -> int | None:
    candidates = [explicit_count, getattr(config, "FOLLOWER_COUNT", None)]
    if normalize_platform_target(platform_target) == "youtube":
        candidates.append(getattr(config, "YOUTUBE_DEFAULT_PARTICIPANT_COUNT", 1000))

    for candidate in candidates:
        try:
            value = int(candidate)
        except Exception:
            continue
        if value > 0:
            return value
    return None


def get_youtube_game_profile(game_mode: str) -> dict[str, Any]:
    raw_profiles = getattr(config, "YOUTUBE_GAME_PROFILES", {})
    if not isinstance(raw_profiles, dict):
        return {}
    profile = raw_profiles.get(str(game_mode or "").strip().lower())
    if not isinstance(profile, dict):
        return {}
    return dict(profile)


def format_profile_text(template: str | None, participant_count: int | None) -> str:
    text = str(template or "").strip()
    count = max(0, int(participant_count or 0))
    if not text:
        return ""
    try:
        return text.format(count=f"{count:,}", participant_count=f"{count:,}")
    except Exception:
        return text


def video_meta_sidecar_path(output_video_path: str | Path) -> Path:
    output_path = Path(output_video_path)
    return output_path.with_suffix(f"{output_path.suffix}.meta.json")


def write_video_meta_sidecar(output_video_path: str | Path, payload: dict[str, Any]) -> Path:
    sidecar_path = video_meta_sidecar_path(output_video_path)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return sidecar_path
