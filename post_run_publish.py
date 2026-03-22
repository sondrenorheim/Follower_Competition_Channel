#!/usr/bin/env python3
"""
Post-run publisher:
- Push updated stats/history to GitHub.
- Upload generated game videos as Reels via instagrapi session.

Usage:
  set IG_SESSION_FILE=path\to\insta_session.json
  python post_run_publish.py --session-file path\to\insta_session.json \
      [--caption-template "{game_mode} Day {day_number}"] \
      [--push-message "Auto-update stats"]
"""

import argparse
import json
import os
import subprocess
import sys
import time
import random
import re
import threading
import webbrowser
from functools import lru_cache
from pathlib import Path

import config
import requests
from shared import auto_push, statistics, game_history
from instagrapi import Client
from shared import statistics, game_history
from shared.platform_targets import (
    is_native_youtube_game,
    normalize_platform_target,
    resolve_output_video_path,
    resolve_record_game_type,
)
try:
    from shared.facebook_media_map import remember_mapping as remember_facebook_media_mapping
except Exception:
    remember_facebook_media_mapping = None
try:
    from shared.youtube_media_map import remember_mapping as remember_youtube_media_mapping
except Exception:
    remember_youtube_media_mapping = None
try:
    from shared.video_variant_builder import (
        ensure_non_ig_join_variant,
        get_last_non_ig_variant_build_info,
        ensure_youtube_short_variant,
        get_last_youtube_variant_build_info,
    )
except Exception:
    ensure_non_ig_join_variant = None
    get_last_non_ig_variant_build_info = None
    ensure_youtube_short_variant = None
    get_last_youtube_variant_build_info = None
try:
    from shared.snapchat_uploader import (
        build_authorize_url as build_snapchat_authorize_url,
        exchange_code_for_tokens as exchange_snapchat_code_for_tokens,
        upload_snapchat,
        write_token_payload as write_snapchat_token_payload,
    )
except Exception:
    build_snapchat_authorize_url = None
    exchange_snapchat_code_for_tokens = None
    write_snapchat_token_payload = None
    upload_snapchat = None
try:
    from safe_snapchat_uploader import SafeSnapchatUploader
except Exception:
    SafeSnapchatUploader = None
try:
    from shared.x_uploader import upload_x
except Exception:
    upload_x = None
try:
    from safe_x_uploader import SafeXUploader
except Exception:
    SafeXUploader = None
try:
    from safe_lemon8_uploader import SafeLemon8Uploader
except Exception:
    SafeLemon8Uploader = None
try:
    from safe_rednote_uploader import SafeRednoteUploader
except Exception:
    SafeRednoteUploader = None

_LOG_HANDLES = []
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_IG_SESSION_FILE = PROJECT_ROOT / "sessions" / "session_followerbattlegrounds.json"
DEFAULT_TIKTOK_SESSION_FILE = PROJECT_ROOT / "tiktok_follower_account_sessionid.json"
_YOUTUBE_COMMENT_LIBS = None
_YOUTUBE_COMMENT_LIBS_FAILED = False
_YOUTUBE_COMMENT_CLIENT = None
_YOUTUBE_COMMENT_CLIENT_LOCK = threading.Lock()


def _configure_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_utf8_output()


def _normalize_smb_mode(game_mode: str | None):
    try:
        from super_follower_bros_shared.levels import normalize_smb_mode
    except Exception:
        return None
    return normalize_smb_mode(game_mode)


def _is_smb_mode(game_mode: str | None) -> bool:
    return _normalize_smb_mode(game_mode) is not None


def _is_jetpack_mode(game_mode: str | None) -> bool:
    return str(game_mode or "").strip().lower() == "jetpack_followers"


def _is_crossy_mode(game_mode: str | None) -> bool:
    return str(game_mode or "").strip().lower() == "crossy_followers"


def _display_day_for_mode(game_mode: str, actual_day_number: int) -> int:
    try:
        day_value = int(actual_day_number)
    except Exception:
        day_value = int(getattr(config, "DAY_NUMBER", 0) or 0)

    if _is_smb_mode(game_mode):
        offset = int(getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71) or 71)
        return max(1, day_value - offset)

    if _is_jetpack_mode(game_mode):
        offset = int(
            getattr(
                config,
                "JETPACK_FOLLOWERS_DAY_OFFSET",
                getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71),
            ) or 0
        )
        return max(1, day_value - offset)

    if _is_crossy_mode(game_mode):
        offset = int(
            getattr(
                config,
                "CROSSY_FOLLOWERS_DAY_OFFSET",
                getattr(
                    config,
                    "JETPACK_FOLLOWERS_DAY_OFFSET",
                    getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71),
                ),
            ) or 0
        )
        return max(1, day_value - offset)

    return day_value


def _is_mode_in_skip_list(game_mode: str, skip_modes) -> bool:
    mode_set = set(skip_modes or [])
    if game_mode in mode_set:
        return True
    if _is_smb_mode(game_mode):
        return "super_follower_bros" in mode_set or "super_follower_bros_1_2" in mode_set
    return False


def _pid_is_running(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _start_process_in_new_console(
    command: list[str],
    cwd: str,
    hidden: bool = False,
    log_path: Path | None = None,
    env: dict | None = None,
):
    try:
        stdout_target = None
        stderr_target = None
        if hidden and log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, "a", encoding="utf-8")
            _LOG_HANDLES.append(log_file)
            stdout_target = log_file
            stderr_target = log_file

        if os.name == "nt":
            if hidden:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            else:
                flags = subprocess.CREATE_NEW_CONSOLE
            subprocess.Popen(
                command,
                cwd=cwd,
                creationflags=flags,
                stdout=stdout_target,
                stderr=stderr_target,
                env=env,
            )
        else:
            subprocess.Popen(
                command,
                cwd=cwd,
                start_new_session=True,
                stdout=stdout_target,
                stderr=stderr_target,
                env=env,
            )
        return True
    except Exception as exc:
        print(f"Warning: Failed to start process {command}: {exc}")
        return False


def _ensure_discord_bot():
    if not getattr(config, "AUTO_START_DISCORD_BOT", False):
        return

    base_dir = Path(__file__).resolve().parent
    log_dir = Path(getattr(config, "DISCORD_BOT_LOG_DIR", "logs/discord_bot"))
    hidden = bool(getattr(
        config,
        "DISCORD_BOT_HEADLESS",
        getattr(config, "WEBHOOK_SERVICE_HEADLESS", False),
    ))

    script_name = getattr(config, "DISCORD_BOT_SCRIPT", "discord_bot/bot.py")
    script_path = base_dir / script_name
    if not script_path.exists():
        print(f"Warning: Discord bot script not found at {script_path}")
        return

    pid_path = Path(getattr(config, "DISCORD_BOT_PID_FILE", "discord_bot/discord_bot.pid"))
    if not pid_path.is_absolute():
        pid_path = base_dir / pid_path

    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except Exception:
            pid = None
        if pid and _pid_is_running(pid):
            return
        try:
            pid_path.unlink()
        except Exception:
            pass

    print("Discord bot not running. Starting discord_bot/bot.py...")
    bot_env = None
    if hidden:
        bot_env = dict(os.environ)
        bot_env["PYTHONUNBUFFERED"] = "1"
    _start_process_in_new_console(
        [sys.executable, str(script_path)],
        str(base_dir),
        hidden=hidden,
        log_path=log_dir / "discord_bot.log",
        env=bot_env,
    )


def build_video_path(game_mode: str, day_number: int | None = None) -> Path:
    """
    Build the expected video output path for a game mode using the config helper.
    Assumes TEST_MODE was False when videos were generated.
    """
    filename = config.get_output_video_path(game_mode=game_mode, day_number=day_number, test_mode=False)
    return Path(filename)


def build_platform_video_path(
    game_mode: str,
    day_number: int | None = None,
    platform_target: str | None = None,
) -> Path:
    filename = resolve_output_video_path(
        game_mode=game_mode,
        day_number=day_number,
        test_mode=False,
        platform_target=normalize_platform_target(platform_target),
    )
    return Path(filename)


def build_non_ig_variant_video_path(game_mode: str, day_number: int | None = None) -> Path:
    if hasattr(config, "get_non_ig_variant_video_path"):
        filename = config.get_non_ig_variant_video_path(
            game_mode=game_mode,
            day_number=day_number,
            test_mode=False,
        )
        return Path(filename)
    base_path = build_video_path(game_mode=game_mode, day_number=day_number)
    suffix = str(getattr(config, "NON_IG_VARIANT_SUFFIX", "_non_ig_join") or "_non_ig_join")
    return base_path.with_name(f"{base_path.stem}{suffix}{base_path.suffix}")


def build_youtube_variant_video_path(game_mode: str, day_number: int | None = None) -> Path:
    if hasattr(config, "get_youtube_variant_video_path"):
        filename = config.get_youtube_variant_video_path(
            game_mode=game_mode,
            day_number=day_number,
            test_mode=False,
        )
        return Path(filename)
    base_path = build_video_path(game_mode=game_mode, day_number=day_number)
    suffix = str(getattr(config, "YOUTUBE_VARIANT_SUFFIX", "_youtube_short") or "_youtube_short")
    return base_path.with_name(f"{base_path.stem}{suffix}{base_path.suffix}")


def _resolve_non_ig_route_platforms() -> set[str]:
    raw = getattr(
        config,
        "NON_IG_VARIANT_AUTO_ROUTE_PLATFORMS",
        ["facebook", "tiktok", "youtube", "snapchat", "x", "lemon8", "rednote"],
    )
    values: list[str]
    if isinstance(raw, str):
        values = [part.strip().lower() for part in raw.split(",")]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(part).strip().lower() for part in raw]
    else:
        values = []
    return {value for value in values if value}


def _resolve_non_ig_variant_enabled() -> bool:
    return _parse_bool(getattr(config, "NON_IG_VARIANT_ENABLED", True), True)


def _resolve_non_ig_generate_on_upload_if_missing() -> bool:
    return _parse_bool(
        getattr(config, "NON_IG_VARIANT_GENERATE_ON_UPLOAD_IF_MISSING", True),
        True,
    )


def _resolve_youtube_variant_enabled() -> bool:
    return _parse_bool(getattr(config, "YOUTUBE_VARIANT_ENABLED", True), True)


def _resolve_youtube_variant_generate_on_upload_if_missing() -> bool:
    return _parse_bool(
        getattr(config, "YOUTUBE_VARIANT_GENERATE_ON_UPLOAD_IF_MISSING", True),
        True,
    )


def resolve_platform_video_path(
    base_video_path: Path,
    platform: str,
    game_mode: str,
    day_number: int | None,
) -> Path | None:
    normalized_platform = str(platform or "").strip().lower()

    if normalized_platform == "youtube" and _resolve_youtube_variant_enabled():
        youtube_variant_path = build_youtube_variant_video_path(
            game_mode=game_mode,
            day_number=day_number,
        )

        if is_native_youtube_game(game_mode, "youtube"):
            try:
                if youtube_variant_path.exists():
                    print(f"Using native YouTube artifact: {youtube_variant_path}")
                    return youtube_variant_path
            except Exception:
                pass
            print(
                f"[WARN] Missing native YouTube artifact for {game_mode}: {youtube_variant_path}. "
                "Skipping upload instead of generating the generic YouTube variant."
            )
            return None

        base_mtime = None
        try:
            base_mtime = base_video_path.stat().st_mtime
        except Exception:
            base_mtime = None

        try:
            if youtube_variant_path.exists():
                variant_mtime = youtube_variant_path.stat().st_mtime
                if base_mtime is None or variant_mtime >= base_mtime:
                    print(f"Using YouTube Shorts variant: {youtube_variant_path}")
                    return youtube_variant_path
        except Exception:
            pass

        if (
            _resolve_youtube_variant_generate_on_upload_if_missing()
            and ensure_youtube_short_variant is not None
        ):
            try:
                resolved_path = ensure_youtube_short_variant(base_video_path, youtube_variant_path)
                if resolved_path == youtube_variant_path and youtube_variant_path.exists():
                    message = f"Generated YouTube Shorts variant: {youtube_variant_path}"
                    if get_last_youtube_variant_build_info is not None:
                        info = get_last_youtube_variant_build_info() or {}
                        build_meta = info.get("build_meta") or {}
                        duration = build_meta.get("duration_seconds")
                        if duration is not None:
                            message += f" (hook={duration:.2f}s)"
                    print(message)
                    print(f"Using YouTube Shorts variant: {youtube_variant_path}")
                    return youtube_variant_path
            except Exception as exc:
                print(f"[WARN] Failed to generate YouTube Shorts variant: {exc}")

        print(
            f"[WARN] Missing YouTube Shorts variant: {youtube_variant_path}. "
            "Falling back to generic non-IG routing if available."
        )

    route_platforms = _resolve_non_ig_route_platforms()
    if not _resolve_non_ig_variant_enabled() or normalized_platform not in route_platforms:
        return base_video_path

    variant_video_path = build_non_ig_variant_video_path(game_mode=game_mode, day_number=day_number)

    base_mtime = None
    try:
        base_mtime = base_video_path.stat().st_mtime
    except Exception:
        base_mtime = None

    try:
        if variant_video_path.exists():
            variant_mtime = variant_video_path.stat().st_mtime
            if base_mtime is None or variant_mtime >= base_mtime:
                print(f"Using non-IG variant for {normalized_platform}: {variant_video_path}")
                return variant_video_path
    except Exception:
        pass

    if _resolve_non_ig_generate_on_upload_if_missing() and ensure_non_ig_join_variant is not None:
        try:
            resolved_path = ensure_non_ig_join_variant(base_video_path, variant_video_path)
            if resolved_path == variant_video_path and variant_video_path.exists():
                message = f"Generated non-IG JOIN variant: {variant_video_path}"
                if get_last_non_ig_variant_build_info is not None:
                    info = get_last_non_ig_variant_build_info() or {}
                    top_y = info.get("top_y")
                    mode = str(info.get("placement_mode") or "").strip()
                    if top_y is not None:
                        if mode:
                            message += f" (top_y={top_y}, mode={mode})"
                        else:
                            message += f" (top_y={top_y})"
                print(message)
                print(f"Using non-IG variant for {normalized_platform}: {variant_video_path}")
                return variant_video_path
        except Exception as exc:
            print(f"[WARN] Failed to generate non-IG variant for {normalized_platform}: {exc}")

    print(
        f"[WARN] Missing non-IG variant for {normalized_platform}: {variant_video_path}. "
        "Skipping upload for this platform (no base fallback)."
    )
    return None


def _iso_timestamp_to_epoch(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(normalized).timestamp()
    except Exception:
        return None


def wait_for_video(path: Path, max_seconds: int, poll_seconds: int, min_mtime: float | None = None) -> bool:
    """Wait for a video file to appear on disk."""
    def _is_ready() -> bool:
        if not path.exists():
            return False
        if min_mtime is None:
            return True
        try:
            return path.stat().st_mtime >= min_mtime
        except Exception:
            return False

    if _is_ready():
        return True
    if max_seconds == 0:
        return False
    start = time.time()
    while True:
        elapsed = time.time() - start
        if max_seconds > 0 and elapsed >= max_seconds:
            return False
        time.sleep(max(1, poll_seconds))
        if _is_ready():
            return True


@lru_cache(maxsize=None)
def load_day_summary(day_number: int) -> dict | None:
    day_path = Path("website/public/api/days") / f"{day_number}.json"
    if not day_path.exists():
        return None
    try:
        with day_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to read day summary {day_path}: {e}")
        return None


@lru_cache(maxsize=None)
def load_game_results(game_id: str) -> dict | None:
    game_path = Path("website/public/api/games") / f"{game_id}.json"
    if not game_path.exists():
        return None
    try:
        with game_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to read game results {game_path}: {e}")
        return None


def _load_partitioned_games(base_dir: str = "website/public/api") -> list[dict]:
    try:
        games_dir = Path(base_dir) / "games"
        if not games_dir.exists():
            return []
        games = []
        for path in games_dir.glob("*.json"):
            if path.name.endswith("_top.json"):
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("game_id"):
                    games.append(data)
            except Exception:
                continue
        return games
    except Exception:
        return []


def _merge_games(primary: list[dict], secondary: list[dict]) -> list[dict]:
    merged = {g.get("game_id"): g for g in primary if isinstance(g, dict) and g.get("game_id")}
    for game in secondary:
        if not isinstance(game, dict):
            continue
        game_id = game.get("game_id")
        if not game_id:
            continue
        existing = merged.get(game_id)
        if existing is None or len(game.get("results", []) or []) > len(existing.get("results", []) or []):
            merged[game_id] = game
    return list(merged.values())


def get_top_usernames_for_game(day_number: int, game_mode: str, limit: int = 10) -> list[str]:
    day_data = load_day_summary(day_number)
    if not day_data:
        return []

    games = [
        g for g in day_data.get("games", [])
        if g.get("game_type") == game_mode
    ]
    if not games:
        return []

    game_summary = max(games, key=lambda g: g.get("timestamp", ""))
    game_id = game_summary.get("game_id")
    if not game_id:
        return []

    game_data = load_game_results(game_id)
    if not game_data:
        return []

    results = game_data.get("results", []) or []
    if not results:
        return []

    sorted_results = sorted(
        results,
        key=lambda r: r.get("placement", r.get("rank", 0) or 0)
    )
    usernames = []
    for result in sorted_results:
        username = result.get("username")
        if not username:
            continue
        usernames.append(username)
        if len(usernames) >= limit:
            break

    return usernames


def format_top_users_block(usernames: list[str]) -> str:
    if not usernames:
        return ""
    lines = ["", "Top 10 in this race:"]
    for idx, username in enumerate(usernames, start=1):
        handle = username if username.startswith("@") else f"@{username}"
        lines.append(f"{idx}. {handle}")
    return "\n".join(lines)


def build_x_post_text(caption: str, game_mode: str, day_number: int) -> str:
    first_line = ""
    for line in str(caption or "").splitlines():
        cleaned = line.strip()
        if cleaned:
            first_line = cleaned
            break
    if not first_line:
        first_line = f"Day {day_number} of making my followers battle every day."
    mode_label = str(game_mode or "").replace("_", " ").strip().title() or "Follower Battlegrounds"
    text = f"{first_line}\nGame: {mode_label} | Day {day_number}\n#followerbattlegrounds"
    return text[:280]


def build_snapchat_post_text(caption: str, game_mode: str, day_number: int) -> str:
    first_line = ""
    for line in str(caption or "").splitlines():
        cleaned = line.strip()
        if cleaned:
            first_line = cleaned
            break
    if not first_line:
        first_line = f"Day {day_number} of making my followers battle every day."
    mode_label = str(game_mode or "").replace("_", " ").strip().title() or "Follower Battlegrounds"
    text = f"{first_line}\nGame: {mode_label} | Day {day_number}"
    return text[:160]


def build_lemon8_post_text(caption: str, game_mode: str, day_number: int) -> str:
    first_line = ""
    for line in str(caption or "").splitlines():
        cleaned = line.strip()
        if cleaned:
            first_line = cleaned
            break
    if not first_line:
        first_line = f"Day {day_number} of making my followers battle every day."
    mode_label = str(game_mode or "").replace("_", " ").strip().title() or "Follower Battlegrounds"
    text = (
        f"{first_line}\n"
        f"Game: {mode_label} | Day {day_number}\n"
        "#followerbattlegrounds #dailygame #creator"
    )
    return text[:400]


def build_rednote_post_text(caption: str, game_mode: str, day_number: int) -> str:
    first_line = ""
    for line in str(caption or "").splitlines():
        cleaned = line.strip()
        if cleaned:
            first_line = cleaned
            break
    if not first_line:
        first_line = f"Day {day_number} of making my followers battle every day."
    mode_label = str(game_mode or "").replace("_", " ").strip().title() or "Follower Battlegrounds"
    text = (
        f"{first_line}\n"
        f"Game: {mode_label} | Day {day_number}\n"
        "#followerbattlegrounds #dailygame #rednote"
    )
    return text[:1000]


def load_client(session_file: Path) -> Client:
    if not session_file.exists():
        raise FileNotFoundError(f"Session file not found: {session_file}")
    cl = Client()
    cl.load_settings(session_file)
    try:
        cl.get_timeline_feed()  # sanity check
    except Exception as e:
        raise SystemExit(
            "Instagram session invalid or blocked. Refresh the session file or use --ig-uploader safe."
        ) from e
    return cl


def load_tiktok_session(session_file: Path) -> str:
    if not session_file.exists():
        raise FileNotFoundError(f"TikTok session file not found: {session_file}")
    import json

    with open(session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    session_id = data.get("sessionid")
    if not session_id:
        raise ValueError(f"Missing 'sessionid' in {session_file}")
    return session_id


def wait_for_manual_login(profile_url: str):
    if not profile_url:
        profile_url = "https://www.instagram.com/accounts/login/"
    print(f"Opening browser for manual login: {profile_url}")
    try:
        webbrowser.open_new_tab(profile_url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
    input("Log in and navigate to your profile page, then press Enter to continue...")


def upload_videos(
    cl: Client,
    video_paths: list[Path],
    caption_template: str,
    delay_seconds: int,
    day_number: int | None = None,
):
    for idx, video_path in enumerate(video_paths):
        if not video_path.exists():
            print(f"[WARN] Skipping missing video: {video_path}")
            continue
        game_mode = video_path.stem.split("_day_")[0] if "_day_" in video_path.stem else video_path.stem
        actual_day_number = int(day_number) if day_number is not None else int(getattr(config, "DAY_NUMBER", 0))
        day_value = _display_day_for_mode(game_mode, actual_day_number)
        caption = caption_template.format(game_mode=game_mode, day_number=day_value)
        skip_top10_modes = set(getattr(config, "TOP10_SKIP_GAME_MODES", []))
        if not _is_mode_in_skip_list(game_mode, skip_top10_modes):
            top_users = get_top_usernames_for_game(actual_day_number, game_mode, limit=10)
            caption += format_top_users_block(top_users)
        print(f"[INFO] Uploading {video_path} as Reel with caption:\n{caption}")
        media = cl.clip_upload(str(video_path), caption=caption)
        print(f"[OK] Uploaded: {video_path.name} -> {media.pk}")

        # Delay handled after TikTok upload
def upload_instagram(cl: Client, video_path: Path, caption: str) -> bool:
    try:
        media = cl.clip_upload(str(video_path), caption=caption)
        print(f"[OK] IG uploaded: {video_path.name} -> {media.pk}")
        return True
    except Exception as e:
        print(f"[WARN] IG upload failed for {video_path.name}: {e}")
        # One retry after longer delay (avoid automation detection)
        try:
            retry_delay = random.randint(30, 60)  # 30-60 seconds
            print(f"   Waiting {retry_delay}s before retry...")
            time.sleep(retry_delay)
            media = cl.clip_upload(str(video_path), caption=caption)
            print(f"[OK] IG uploaded on retry: {video_path.name} -> {media.pk}")
            return True
        except Exception as e2:
            print(f"[ERROR] IG upload retry failed for {video_path.name}: {e2}")
            return False


def save_instagram_cookies(cookies_file: Path) -> bool:
    try:
        from safe_instagram_uploader import SafeInstagramUploader
    except Exception as e:
        print(f"IG safe uploader unavailable: {e}")
        return False
    uploader = SafeInstagramUploader(cookies_file=str(cookies_file), headless=False)
    uploader.save_cookies()
    return True


def upload_instagram_safe(
    video_path: Path,
    caption: str,
    cookies_file: Path,
    headless: bool,
    game_mode: str | None = None,
) -> bool:
    try:
        from safe_instagram_uploader import SafeInstagramUploader
    except Exception as e:
        print(f"IG safe uploader unavailable: {e}")
        return False
    uploader = SafeInstagramUploader(cookies_file=str(cookies_file), headless=headless)
    return uploader.upload_reel(str(video_path), caption, game_mode=game_mode)


def _facebook_response_body(response: requests.Response) -> dict:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {"raw": str(getattr(response, "text", "") or "")[:500]}


def _upload_facebook_page_video_single_request(
    endpoint: str,
    video_path: Path,
    payload: dict,
) -> dict | None:
    try:
        with video_path.open("rb") as source_file:
            response = requests.post(
                endpoint,
                data=payload,
                files={"source": (video_path.name, source_file, "video/mp4")},
                timeout=(30, 1800),
            )
    except Exception as e:
        print(f"[ERROR] FB upload request failed for {video_path.name}: {e}")
        return None

    body = _facebook_response_body(response)
    if not response.ok:
        print(f"[ERROR] FB upload failed for {video_path.name}: HTTP {response.status_code} {body}")
        return None

    return {
        "body": body,
        "video_id": str(body.get("id") or body.get("video_id") or "").strip(),
        "post_id": str(body.get("post_id") or "").strip(),
    }


def _upload_facebook_page_video_resumable(
    endpoint: str,
    video_path: Path,
    access_token: str,
    title: str,
    description: str,
) -> dict | None:
    try:
        file_size = int(video_path.stat().st_size)
    except Exception as exc:
        print(f"[ERROR] FB resumable upload stat failed for {video_path.name}: {exc}")
        return None

    start_payload = {
        "upload_phase": "start",
        "file_size": str(file_size),
        "access_token": access_token,
    }
    try:
        start_response = requests.post(endpoint, data=start_payload, timeout=(30, 120))
    except Exception as exc:
        print(f"[ERROR] FB resumable start failed for {video_path.name}: {exc}")
        return None

    start_body = _facebook_response_body(start_response)
    if not start_response.ok:
        print(
            f"[ERROR] FB resumable start failed for {video_path.name}: "
            f"HTTP {start_response.status_code} {start_body}"
        )
        return None

    upload_session_id = str(start_body.get("upload_session_id") or "").strip()
    if not upload_session_id:
        print(f"[ERROR] FB resumable start missing upload_session_id for {video_path.name}: {start_body}")
        return None

    start_offset = str(start_body.get("start_offset") or "0").strip()
    end_offset = str(start_body.get("end_offset") or "0").strip()
    chunk_count = 0
    print(f"[INFO] FB resumable upload started: {video_path.name} ({file_size / (1024 * 1024):.1f} MB)")

    try:
        with video_path.open("rb") as source_file:
            # Guard against unexpected offset loops.
            for _ in range(100000):
                if start_offset == end_offset:
                    break

                try:
                    start_int = int(start_offset)
                    end_int = int(end_offset)
                except Exception:
                    print(
                        f"[ERROR] FB resumable transfer invalid offsets for {video_path.name}: "
                        f"start={start_offset} end={end_offset}"
                    )
                    return None

                if end_int <= start_int:
                    print(
                        f"[ERROR] FB resumable transfer non-increasing offsets for {video_path.name}: "
                        f"start={start_int} end={end_int}"
                    )
                    return None

                source_file.seek(start_int)
                chunk = source_file.read(end_int - start_int)
                if not chunk:
                    print(
                        f"[ERROR] FB resumable transfer empty chunk for {video_path.name}: "
                        f"start={start_int} end={end_int}"
                    )
                    return None

                transfer_payload = {
                    "upload_phase": "transfer",
                    "upload_session_id": upload_session_id,
                    "start_offset": start_offset,
                    "access_token": access_token,
                }
                transfer_response = requests.post(
                    endpoint,
                    data=transfer_payload,
                    files={"video_file_chunk": ("chunk.bin", chunk, "application/octet-stream")},
                    timeout=(30, 900),
                )
                transfer_body = _facebook_response_body(transfer_response)
                if not transfer_response.ok:
                    print(
                        f"[ERROR] FB resumable transfer failed for {video_path.name}: "
                        f"HTTP {transfer_response.status_code} {transfer_body}"
                    )
                    return None

                next_start = str(transfer_body.get("start_offset") or "").strip()
                next_end = str(transfer_body.get("end_offset") or "").strip()
                if not next_start or not next_end:
                    print(
                        f"[ERROR] FB resumable transfer response missing offsets for {video_path.name}: "
                        f"{transfer_body}"
                    )
                    return None
                if next_start == start_offset and next_end == end_offset:
                    print(
                        f"[ERROR] FB resumable transfer stalled for {video_path.name}: "
                        f"start={start_offset} end={end_offset}"
                    )
                    return None

                chunk_count += 1
                start_offset, end_offset = next_start, next_end
                if chunk_count % 5 == 0 or start_offset == end_offset:
                    try:
                        uploaded = min(file_size, int(start_offset))
                    except Exception:
                        uploaded = 0
                    pct = (uploaded / file_size * 100.0) if file_size > 0 else 100.0
                    print(
                        f"[INFO] FB transfer progress: {pct:.1f}% "
                        f"({uploaded // (1024 * 1024)}MB/{file_size // (1024 * 1024)}MB)"
                    )
            else:
                print(f"[ERROR] FB resumable transfer loop overflow for {video_path.name}")
                return None
    except Exception as exc:
        print(f"[ERROR] FB resumable transfer exception for {video_path.name}: {exc}")
        return None

    finish_payload = {
        "upload_phase": "finish",
        "upload_session_id": upload_session_id,
        "title": title,
        "description": description,
        "published": "true",
        "access_token": access_token,
    }
    try:
        finish_response = requests.post(endpoint, data=finish_payload, timeout=(30, 300))
    except Exception as exc:
        print(f"[ERROR] FB resumable finish failed for {video_path.name}: {exc}")
        return None

    finish_body = _facebook_response_body(finish_response)
    if not finish_response.ok:
        print(
            f"[ERROR] FB resumable finish failed for {video_path.name}: "
            f"HTTP {finish_response.status_code} {finish_body}"
        )
        return None

    video_id = str(
        finish_body.get("video_id")
        or finish_body.get("id")
        or start_body.get("video_id")
        or start_body.get("id")
        or ""
    ).strip()
    post_id = str(finish_body.get("post_id") or "").strip()
    body = dict(finish_body)
    if video_id and not body.get("video_id") and not body.get("id"):
        body["video_id"] = video_id
    if upload_session_id and not body.get("upload_session_id"):
        body["upload_session_id"] = upload_session_id
    body["resumable"] = True

    return {
        "body": body,
        "video_id": video_id,
        "post_id": post_id,
    }


def upload_facebook_page_video(
    video_path: Path,
    caption: str,
    page_id: str,
    access_token: str,
    api_version: str = "v18.0",
    game_mode: str | None = None,
    day_number: int | None = None,
) -> dict | None:
    if not page_id:
        print("[WARN] FB upload skipped: missing Facebook Page ID.")
        return None
    if not access_token:
        print("[WARN] FB upload skipped: missing Facebook Page access token.")
        return None
    if not video_path.exists():
        print(f"[WARN] FB upload skipped: missing video {video_path}")
        return None

    version = str(api_version or "v18.0").strip().lstrip("/")
    endpoint = f"https://graph-video.facebook.com/{version}/{page_id}/videos"
    join_prompt_mode = _resolve_facebook_join_prompt_mode()
    join_prompt_text = _resolve_facebook_join_prompt_text()
    title = (caption.splitlines()[0].strip() if caption else "") or video_path.stem
    description = str(caption or "")
    if join_prompt_text and join_prompt_mode in {"title", "both"}:
        # Facebook feed cards often ignore the video title; keep CTA visible in description too.
        if join_prompt_text.lower() not in description.lower():
            description = f"{join_prompt_text}\n\n{description}".strip()
    if join_prompt_text and join_prompt_mode in {"title", "both"}:
        title = join_prompt_text
    if len(title) > 250:
        title = title[:250]

    payload = {
        "description": description,
        "title": title,
        "published": "true",
        "access_token": access_token,
    }

    upload_result = _upload_facebook_page_video_resumable(
        endpoint=endpoint,
        video_path=video_path,
        access_token=access_token,
        title=title,
        description=description,
    )
    if upload_result is None:
        print(f"[WARN] FB resumable upload failed for {video_path.name}; trying single-request fallback.")
        upload_result = _upload_facebook_page_video_single_request(
            endpoint=endpoint,
            video_path=video_path,
            payload=payload,
        )
    if upload_result is None:
        return None

    body = upload_result.get("body") or {}
    video_id = str(upload_result.get("video_id") or "").strip()
    post_id = str(upload_result.get("post_id") or "").strip()
    metadata = fetch_facebook_object_metadata(video_id or post_id, access_token, api_version=version)
    if metadata:
        post_id = post_id or str(metadata.get("post_id") or "").strip()
    permalink = str(body.get("permalink_url") or metadata.get("permalink_url") or "").strip()

    if video_id or post_id:
        print(f"[OK] FB uploaded: {video_path.name} -> {video_id or post_id}")
    else:
        print(f"[OK] FB upload response for {video_path.name}: {body}")

    if join_prompt_text and join_prompt_mode in {"comment", "both"}:
        def _build_comment_targets() -> list[str]:
            values: list[str] = []
            for candidate in (
                post_id,
                video_id,
                str(body.get("id") or "").strip(),
                str(body.get("post_id") or "").strip(),
            ):
                candidate = str(candidate or "").strip()
                if candidate and candidate not in values:
                    values.append(candidate)
            # Graph APIs sometimes return short post ids; include page-scoped fallback.
            expanded = list(values)
            for candidate in values:
                if "_" not in candidate and page_id:
                    expanded_id = f"{page_id}_{candidate}"
                    if expanded_id not in expanded:
                        expanded.append(expanded_id)
            return expanded

        cta_posted = False
        for attempt_index, delay_seconds in enumerate((0.0, 2.0, 5.0), start=1):
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            # Re-fetch metadata in case post id appears shortly after upload finalize.
            refreshed = fetch_facebook_object_metadata(video_id or post_id, access_token, api_version=version)
            if refreshed:
                post_id = post_id or str(refreshed.get("post_id") or "").strip()
            targets = _build_comment_targets()
            for target_id in targets:
                if post_facebook_comment(target_id, join_prompt_text, access_token, api_version=version):
                    print(f"[OK] FB JOIN CTA comment posted on {target_id} (attempt {attempt_index})")
                    cta_posted = True
                    break
            if cta_posted:
                break
        if not cta_posted:
            print("[WARN] FB JOIN CTA comment could not be posted on any upload target.")

    if game_mode and day_number and remember_facebook_media_mapping is not None:
        try:
            map_extra = {
                "permalink": permalink,
                "caption_excerpt": str(caption or "")[:240],
                "video_filename": video_path.name,
            }
            mapping_result = remember_facebook_media_mapping(
                _resolve_facebook_media_map_path(),
                video_id=video_id or None,
                post_id=post_id or None,
                game_type=str(game_mode),
                day_number=int(day_number),
                source="fb_upload",
                extra=map_extra,
            )
            print(f"[OK] FB mapping persisted ({len(mapping_result.get('keys', []))} keys)")
        except Exception as exc:
            print(f"[WARN] Failed to persist FB media mapping: {exc}")

    return {
        "ok": True,
        "video_id": video_id,
        "post_id": post_id,
        "permalink": permalink,
        "raw": body,
    }


def upload_tiktok_cookie_based(video_path: Path, caption: str, username: str = "SingingNarrator", schedule_hours: int = 0):
    """
    Upload to TikTok using TiktokAutoUploader (cookie-based, more reliable)
    """
    # Use local TiktokAutoUploader in this project
    uploader_dir = Path(__file__).parent / "TiktokAutoUploader"
    cli_script = uploader_dir / "cli.py"

    if not cli_script.exists():
        print(f"[ERROR] TiktokAutoUploader not found at: {uploader_dir}")
        print("   Install it or update the path in post_run_publish.py")
        return False

    if not video_path.exists():
        print(f"[WARN] Skipping missing video for TikTok: {video_path}")
        return False

    # Check if cookie file exists
    cookie_path = uploader_dir / "CookiesDir" / f"tiktok_session-{username}.cookie"
    if not cookie_path.exists():
        print(f"[ERROR] TikTok cookie not found: {cookie_path}")
        print(f"   Run the TiktokAutoUploader authentication for user '{username}' first")
        return False

    # Schedule time in seconds (0 = post immediately)
    schedule_time = schedule_hours * 3600 if schedule_hours > 0 else 0
    schedule_msg = f" (scheduled {schedule_hours}h from now)" if schedule_hours > 0 else ""

    # TikTok uploader expects videos in VideosDirPath folder
    # Copy video there temporarily
    import shutil
    videos_dir = uploader_dir / "VideosDirPath"
    videos_dir.mkdir(exist_ok=True)

    temp_video_path = videos_dir / video_path.name
    try:
        shutil.copy2(video_path, temp_video_path)
        print(f"[INFO] Copied video to TikTok uploader folder")
    except Exception as e:
        print(f"[ERROR] Failed to copy video: {e}")
        return False

    # Use just the filename (not full path) since it's now in VideosDirPath
    cmd = [
        "python",
        str(cli_script),
        "upload",
        "-u", username,
        "-v", video_path.name,  # Just filename, not full path
        "-t", caption,
        "-st", str(schedule_time)
    ]

    print(f"[INFO] Uploading to TikTok{schedule_msg}...")

    try:
        import subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,  # 5 minute timeout
            cwd=str(uploader_dir)  # Run from uploader directory
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # Clean up temporary video file
        try:
            temp_video_path.unlink()
        except:
            pass

        if result.returncode == 0:
            print(f"[OK] TikTok upload successful!")
            return True
        else:
            print(f"[ERROR] TikTok upload failed (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print("[ERROR] TikTok upload timed out after 5 minutes")
        # Clean up
        try:
            temp_video_path.unlink()
        except:
            pass
        return False
    except Exception as e:
        print(f"[ERROR] TikTok upload failed: {e}")
        # Clean up
        try:
            temp_video_path.unlink()
        except:
            pass
        return False


def upload_tiktok(session_id: str, video_path: Path, caption: str):
    """
    Legacy function - redirects to cookie-based uploader
    The session_id parameter is ignored in favor of cookie-based auth
    """
    # TODO: Change this to your follower battle TikTok username
    tiktok_username = "followerbattlegro"  # Update this with your actual TikTok username

    return upload_tiktok_cookie_based(
        video_path=video_path,
        caption=caption,
        username=tiktok_username,
        schedule_hours=0  # Post immediately
    )


def upload_youtube(
    video_path: Path,
    game_mode: str,
    day_number: int,
    schedule_hours: int = 0,
    privacy: str = "private",
    *,
    platform_target: str = "instagram",
    record_game_type: str | None = None,
) -> bool:
    """
    Upload to the dedicated YouTube Shorts channel.

    Args:
        video_path: Path to the video file
        game_mode: Game mode (e.g., "team_battle", "battle_royale")
        day_number: Day number of the competition
        schedule_hours: Hours to schedule ahead (0 = upload as private immediately)
        privacy: Privacy status ("private", "unlisted", or "public")

    Returns:
        True if upload successful, False otherwise
    """
    youtube_uploader = Path(__file__).parent / "youtube_uploader.py"

    if not youtube_uploader.exists():
        print(f"[ERROR] YouTube uploader not found: {youtube_uploader}")
        return False

    if not video_path.exists():
        print(f"[WARN] Skipping missing video for YouTube: {video_path}")
        return False

    schedule_msg = f" (scheduled {schedule_hours}h from now)" if schedule_hours > 0 else f" (privacy: {privacy})"
    print(f"[INFO] Uploading to YouTube{schedule_msg}...")

    cmd = [
        "python",
        str(youtube_uploader),
        "--video", str(video_path),
        "--day", str(day_number),
        "--game", game_mode,
        "--platform", normalize_platform_target(platform_target),
        "--privacy", privacy,
    ]

    if schedule_hours > 0:
        cmd.extend(["--schedule-hours", str(schedule_hours)])

    try:
        import subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,  # 10 minute timeout for YouTube
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            output_blob = f"{result.stdout or ''}\n{result.stderr or ''}"
            video_id_match = re.search(r"(?:Video ID:\s*|watch\?v=)([A-Za-z0-9_-]{6,})", output_blob, re.IGNORECASE)
            youtube_video_id = video_id_match.group(1).strip() if video_id_match else ""
            if not youtube_video_id:
                print("[WARN] Could not parse YouTube video id from uploader output; mapping not persisted.")
            if youtube_video_id and remember_youtube_media_mapping is not None:
                try:
                    map_extra = {
                        "video_filename": video_path.name,
                        "privacy": str(privacy or ""),
                        "schedule_hours": float(schedule_hours or 0),
                    }
                    remember_youtube_media_mapping(
                        _resolve_youtube_media_map_path(),
                        video_id=youtube_video_id,
                        game_type=str(record_game_type or game_mode),
                        day_number=int(day_number),
                        source="youtube_upload",
                        extra=map_extra,
                    )
                    print(f"[OK] YouTube mapping persisted for {youtube_video_id}")
                except Exception as exc:
                    print(f"[WARN] Failed to persist YouTube mapping: {exc}")
            if youtube_video_id and _resolve_youtube_upload_join_comment_enabled():
                join_prompt_text = _resolve_youtube_upload_join_comment_text()
                if join_prompt_text:
                    posted = False
                    for attempt_index, delay_seconds in enumerate((0.0, 2.0, 5.0), start=1):
                        if delay_seconds > 0:
                            time.sleep(delay_seconds)
                        if post_youtube_comment(youtube_video_id, join_prompt_text):
                            print(
                                f"[OK] YouTube JOIN CTA comment posted on {youtube_video_id} "
                                f"(attempt {attempt_index})"
                            )
                            posted = True
                            break
                    if not posted:
                        print(f"[WARN] YouTube JOIN CTA comment could not be posted on {youtube_video_id}")
                else:
                    print("[WARN] YouTube JOIN upload-comment enabled, but text is empty.")
            print(f"[OK] YouTube upload successful!")
            return True
        else:
            print(f"[ERROR] YouTube upload failed (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print("[ERROR] YouTube upload timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"[ERROR] YouTube upload failed: {e}")
        return False


def push_stats(commit_message: str | None):
    if getattr(config, "TEST_MODE", False):
        raise SystemExit("TEST_MODE is True: stats/history not saved. Re-run games with TEST_MODE=False before pushing.")
    # Regenerate web bundles before pushing
    try:
        api_games = _load_partitioned_games("website/public/api")
        local_history = game_history.GameHistory("game_history.json")
        merged_games = _merge_games(api_games, local_history.history.get("games", []))
        gh = game_history.GameHistory("game_history.json")
        gh.history = {"games": merged_games}
        if api_games:
            print(f"Using existing API history ({len(api_games)} games) as baseline")
        print(f"Merged local history -> {len(merged_games)} total games")
        gh.export_web_history(output_path="website/public/game_history_web.json")
        print("Regenerated website/public/game_history_web.json")
    except Exception as e:
        print(f"Failed to regenerate game_history.json (web): {e}")
    try:
        games = gh.history.get("games", []) if gh else []
        stats = statistics.PlayerStatistics.rebuild_from_games(
            games,
            stats_file="player_statistics.json",
        )
        stats.export_web_stats(output_path="website/public/player_statistics_web.json")
        print("Regenerated website/public/player_statistics_web.json")
    except Exception as e:
        print(f"Failed to regenerate player_statistics_web.json: {e}")
    ok = auto_push.push_stats_to_github(commit_message=commit_message)
    if not ok:
        raise SystemExit("Git push failed. See logs above.")


def parse_args():
    parser = argparse.ArgumentParser(description="Push stats to GitHub and upload generated videos as Reels.")
    default_snapchat_uploader = str(getattr(config, "SNAPCHAT_UPLOADER", "safe") or "safe").strip().lower()
    if default_snapchat_uploader not in {"api", "safe"}:
        default_snapchat_uploader = "safe"
    default_x_uploader = str(getattr(config, "X_UPLOADER", "api") or "api").strip().lower()
    if default_x_uploader not in {"api", "safe"}:
        default_x_uploader = "api"
    parser.add_argument(
        "--enable-uploads",
        action="store_true",
        help="Enable Instagram/TikTok/YouTube/Snapchat/X/Lemon8/Rednote uploads (default: stats only).",
    )
    parser.add_argument(
        "--skip-instagram",
        action="store_true",
        help="Skip Instagram uploads (useful for Snapchat-only/platform-specific tests).",
    )
    parser.add_argument(
        "--wait-for-login",
        action="store_true",
        help="Open a browser and wait for manual Instagram login before uploading (instagrapi only).",
    )
    parser.add_argument(
        "--ig-uploader",
        choices=["instagrapi", "safe"],
        default="instagrapi",
        help="Instagram uploader backend (default: instagrapi).",
    )
    parser.add_argument(
        "--ig-headless",
        action="store_true",
        help="Run safe uploader in headless mode (only when --ig-uploader safe).",
    )
    parser.add_argument(
        "--ig-cookies-file",
        type=Path,
        default=Path("instagram_cookies.json"),
        help="Path to Instagram cookies JSON for safe uploader (or set IG_COOKIES_FILE).",
    )
    parser.add_argument(
        "--session-file",
        type=Path,
        default=DEFAULT_IG_SESSION_FILE,
        help="Path to instagrapi session JSON (or set IG_SESSION_FILE env var).",
    )
    parser.add_argument(
        "--tiktok-session-file",
        type=Path,
        default=DEFAULT_TIKTOK_SESSION_FILE,
        help="Path to TikTok session JSON with {'sessionid': '...'} (or set TIKTOK_SESSION_FILE).",
    )
    parser.add_argument(
        "--caption-template",
        default="Day {day_number} of making my followers battle every day! Follow to enter the battle!\n\n"
        "Check the link in the bio for your result and overall monthly ranking!\n\n"
        "#followerbattlegrounds\n\n"
        "Game: {game_mode} | Day {day_number}",
        help="Caption template; placeholders: {game_mode}, {day_number}.",
    )
    parser.add_argument(
        "--ig-profile-url",
        default="",
        help="Optional Instagram profile URL to open when --wait-for-login is used.",
    )
    parser.add_argument(
        "--ig-export-followers",
        action="store_true",
        help="Export Instagram follower data via Account Center.",
    )
    parser.add_argument(
        "--ig-export-after-uploads",
        action="store_true",
        help="Run follower export after uploads instead of before.",
    )
    parser.add_argument(
        "--ig-export-profile",
        default="",
        help="Override export profile name (default: config.IG_EXPORT_PROFILE_NAME).",
    )
    parser.add_argument(
        "--ig-export-date-range",
        default="",
        help="Override export date range label (default: config.IG_EXPORT_DATE_RANGE).",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Run Instagram export only (no stats push or uploads).",
    )
    parser.add_argument(
        "--delay-seconds",
        type=int,
        default=None,
        help="Fixed delay between uploads in seconds. If set, randomization of +/-20%% will be applied.",
    )
    parser.add_argument(
        "--upload-interval-minutes",
        type=int,
        default=None,
        help="Fixed delay between uploads in minutes (no jitter; overrides delay-min/max).",
    )
    parser.add_argument(
        "--pre-upload-wait-seconds",
        type=int,
        default=0,
        help="Fixed delay after stats/API publish and before the first upload (default 0).",
    )
    parser.add_argument(
        "--pre-upload-wait-minutes",
        type=int,
        default=None,
        help="Fixed delay in minutes after stats/API publish and before the first upload.",
    )
    parser.add_argument(
        "--delay-min-seconds",
        type=int,
        default=10800,
        help="Minimum delay between uploads in seconds (default 10800 = 3 hours).",
    )
    parser.add_argument(
        "--delay-max-seconds",
        type=int,
        default=14400,
        help="Maximum delay between uploads in seconds (default 14400 = 4 hours).",
    )
    parser.add_argument(
        "--wait-for-videos",
        action="store_true",
        help="Wait for missing videos to appear before uploading.",
    )
    parser.add_argument(
        "--queue-ready-videos",
        action="store_true",
        help="Process videos in run-context order and wait for each video plus per-game data to become ready.",
    )
    parser.add_argument(
        "--wait-forever",
        action="store_true",
        help="When waiting for videos, wait indefinitely until the file appears.",
    )
    parser.add_argument(
        "--wait-max-seconds",
        type=int,
        default=0,
        help="Maximum seconds to wait per missing video (default 0 = no wait; negative = wait forever).",
    )
    parser.add_argument(
        "--wait-poll-seconds",
        type=int,
        default=30,
        help="Polling interval when waiting for videos (default 30).",
    )
    parser.add_argument(
        "--wait-poll-minutes",
        type=int,
        default=None,
        help="Polling interval in minutes when waiting for videos (overrides --wait-poll-seconds).",
    )
    parser.add_argument(
        "--ready-grace-seconds",
        type=int,
        default=0,
        help="Delay after a game's data is detected and before uploading that video (default 0).",
    )
    parser.add_argument(
        "--ready-grace-minutes",
        type=int,
        default=None,
        help="Delay in minutes after a game's data is detected and before uploading that video.",
    )
    parser.add_argument(
        "--events-scan-max-files",
        type=int,
        default=12,
        help="How many recent event log files to scan for per-game readiness checks (default 12).",
    )
    parser.add_argument(
        "--push-message",
        default=None,
        help="Optional git commit message for stats push.",
    )
    parser.add_argument(
        "--skip-stats",
        action="store_true",
        help="Skip stats/history push (uploads only).",
    )
    parser.add_argument(
        "--run-context-file",
        type=Path,
        default=None,
        help="Optional run context JSON (freezes day/modes for uploads).",
    )
    parser.add_argument(
        "--run-day-number",
        type=int,
        default=None,
        help="Override day number for video paths/captions.",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=0,
        help="Limit number of videos processed this run (0 = no limit).",
    )
    parser.add_argument(
        "--skip-youtube",
        action="store_true",
        help="Skip YouTube uploads.",
    )
    parser.add_argument(
        "--youtube-privacy",
        choices=["private", "unlisted", "public"],
        default="public",
        help="YouTube privacy status (default: public).",
    )
    parser.add_argument(
        "--youtube-schedule-hours",
        type=int,
        default=0,
        help="Schedule YouTube upload X hours from now (0 = upload as private immediately).",
    )
    parser.add_argument(
        "--enable-facebook-page-upload",
        action="store_true",
        help="Upload each successful Instagram video to a Facebook Page via Graph API.",
    )
    parser.add_argument(
        "--facebook-page-id",
        default="",
        help="Facebook Page ID for Graph API uploads (or set FACEBOOK_PAGE_ID).",
    )
    parser.add_argument(
        "--facebook-access-token",
        default="",
        help="Page access token for Graph API uploads (or set FACEBOOK_PAGE_ACCESS_TOKEN).",
    )
    parser.add_argument(
        "--facebook-api-version",
        default="",
        help="Graph API version (default from env/config or v18.0).",
    )
    parser.add_argument(
        "--facebook-upload-on-ig-failure",
        action="store_true",
        help="Attempt Facebook Page upload even when Instagram upload is not explicitly confirmed.",
    )
    parser.add_argument(
        "--facebook-secrets-file",
        default="facebook_page_publish.local.env",
        help="Local env-style file for Facebook publish credentials (default: facebook_page_publish.local.env).",
    )
    parser.add_argument(
        "--enable-snapchat-upload",
        action="store_true",
        help="Upload each eligible video to Snapchat (API or safe uploader).",
    )
    parser.add_argument(
        "--snapchat-uploader",
        choices=["api", "safe"],
        default=default_snapchat_uploader,
        help="Snapchat uploader backend (default from config.SNAPCHAT_UPLOADER or safe).",
    )
    parser.add_argument(
        "--snapchat-upload-on-ig-failure",
        action="store_true",
        help="Attempt Snapchat upload even when Instagram upload is not explicitly confirmed.",
    )
    parser.add_argument(
        "--skip-snapchat",
        action="store_true",
        help="Skip Snapchat uploads even if config/env enables them.",
    )
    parser.add_argument(
        "--snapchat-secrets-file",
        default="snapchat_publish.local.env",
        help="Local env-style file for Snapchat credentials (default: snapchat_publish.local.env).",
    )
    parser.add_argument(
        "--snapchat-cookies-file",
        type=Path,
        default=Path(getattr(config, "SNAPCHAT_COOKIES_FILE", "snapchat_cookies.json")),
        help="Path to Snapchat cookies JSON for --snapchat-uploader safe.",
    )
    parser.add_argument(
        "--snapchat-profile-dir",
        default=str(getattr(config, "SNAPCHAT_PROFILE_DIR", "sessions/snapchat_chrome_profile")),
        help="Persistent Chrome profile dir for Snapchat safe uploader session reuse.",
    )
    parser.add_argument(
        "--snapchat-headless",
        action="store_true",
        help="Run safe Snapchat uploader in headless mode.",
    )
    parser.add_argument(
        "--snapchat-save-cookies",
        action="store_true",
        help="Open Snapchat login flow and save cookies for --snapchat-uploader safe, then exit.",
    )
    parser.add_argument(
        "--snapchat-client-id",
        default="",
        help="Snapchat OAuth client id (or set SNAPCHAT_CLIENT_ID).",
    )
    parser.add_argument(
        "--snapchat-client-secret",
        default="",
        help="Snapchat OAuth client secret (or set SNAPCHAT_CLIENT_SECRET).",
    )
    parser.add_argument(
        "--snapchat-redirect-uri",
        default="",
        help="Snapchat OAuth redirect URI (or set SNAPCHAT_REDIRECT_URI).",
    )
    parser.add_argument(
        "--snapchat-profile-id",
        default="",
        help="Snapchat Public Profile ID for posting (or set SNAPCHAT_PROFILE_ID).",
    )
    parser.add_argument(
        "--snapchat-print-auth-url",
        action="store_true",
        help="Print Snapchat OAuth authorize URL and exit.",
    )
    parser.add_argument(
        "--snapchat-auth-code",
        default="",
        help="Exchange Snapchat OAuth authorization code and save tokens, then exit.",
    )
    parser.add_argument(
        "--snapchat-auth-state",
        default="",
        help="Optional OAuth state for --snapchat-print-auth-url.",
    )
    parser.add_argument(
        "--enable-x-upload",
        action="store_true",
        help="Upload each eligible video to X.",
    )
    parser.add_argument(
        "--x-uploader",
        choices=["api", "safe"],
        default=default_x_uploader,
        help="X uploader backend (default from config.X_UPLOADER or api).",
    )
    parser.add_argument(
        "--x-cookies-file",
        type=Path,
        default=Path(getattr(config, "X_COOKIES_FILE", "x_cookies.json")),
        help="Path to X cookies JSON for --x-uploader safe (or set X_COOKIES_FILE).",
    )
    parser.add_argument(
        "--x-headless",
        action="store_true",
        help="Run safe X uploader in headless mode (only with --x-uploader safe).",
    )
    parser.add_argument(
        "--x-save-cookies",
        action="store_true",
        help="Open X login flow and save cookies for --x-uploader safe, then exit.",
    )
    parser.add_argument(
        "--x-upload-on-ig-failure",
        action="store_true",
        help="Attempt X upload even when Instagram upload is not explicitly confirmed.",
    )
    parser.add_argument(
        "--x-upload-before-instagram",
        action="store_true",
        help=(
            "Attempt X upload before Instagram for each video. "
            "If X still requires IG success, upload is deferred until after IG."
        ),
    )
    parser.add_argument(
        "--skip-x",
        action="store_true",
        help="Skip X uploads even if config/env enables them.",
    )
    parser.add_argument(
        "--x-secrets-file",
        default="x_publish.local.env",
        help="Local env-style file for X credentials (default: x_publish.local.env).",
    )
    parser.add_argument(
        "--x-consumer-key",
        default="",
        help="X API consumer key (or set X_CONSUMER_KEY).",
    )
    parser.add_argument(
        "--x-consumer-secret",
        default="",
        help="X API consumer secret (or set X_CONSUMER_SECRET).",
    )
    parser.add_argument(
        "--x-access-token",
        default="",
        help="X access token (or set X_ACCESS_TOKEN).",
    )
    parser.add_argument(
        "--x-access-token-secret",
        default="",
        help="X access token secret (or set X_ACCESS_TOKEN_SECRET).",
    )
    default_lemon8_uploader = str(getattr(config, "LEMON8_UPLOADER", "safe") or "safe").strip().lower()
    if default_lemon8_uploader not in {"safe"}:
        default_lemon8_uploader = "safe"
    parser.add_argument(
        "--enable-lemon8-upload",
        action="store_true",
        help="Upload each eligible video to Lemon8.",
    )
    parser.add_argument(
        "--lemon8-uploader",
        choices=["safe"],
        default=default_lemon8_uploader,
        help="Lemon8 uploader backend (currently only safe).",
    )
    parser.add_argument(
        "--lemon8-cookies-file",
        type=Path,
        default=Path(getattr(config, "LEMON8_COOKIES_FILE", "lemon8_cookies.json")),
        help="Path to Lemon8 cookies JSON for safe uploads.",
    )
    parser.add_argument(
        "--lemon8-headless",
        action="store_true",
        help="Run Lemon8 safe uploader in headless mode.",
    )
    parser.add_argument(
        "--lemon8-save-cookies",
        action="store_true",
        help="Open Lemon8 login flow and save cookies, then exit.",
    )
    parser.add_argument(
        "--lemon8-upload-on-ig-failure",
        action="store_true",
        help="Attempt Lemon8 upload even when Instagram upload is not explicitly confirmed.",
    )
    parser.add_argument(
        "--skip-lemon8",
        action="store_true",
        help="Skip Lemon8 uploads even if config/env enables them.",
    )
    parser.add_argument(
        "--lemon8-secrets-file",
        default="lemon8_publish.local.env",
        help="Local env-style file for Lemon8 settings (default: lemon8_publish.local.env).",
    )
    default_rednote_uploader = str(getattr(config, "REDNOTE_UPLOADER", "safe") or "safe").strip().lower()
    if default_rednote_uploader not in {"safe"}:
        default_rednote_uploader = "safe"
    parser.add_argument(
        "--enable-rednote-upload",
        action="store_true",
        help="Upload each eligible video to Rednote (Xiaohongshu).",
    )
    parser.add_argument(
        "--rednote-uploader",
        choices=["safe"],
        default=default_rednote_uploader,
        help="Rednote uploader backend (currently only safe).",
    )
    parser.add_argument(
        "--rednote-cookies-file",
        type=Path,
        default=Path(getattr(config, "REDNOTE_COOKIES_FILE", "rednote_cookies.json")),
        help="Path to Rednote cookies JSON for safe uploads.",
    )
    parser.add_argument(
        "--rednote-headless",
        action="store_true",
        help="Run Rednote safe uploader in headless mode.",
    )
    parser.add_argument(
        "--rednote-save-cookies",
        action="store_true",
        help="Open Rednote login flow and save cookies, then exit.",
    )
    parser.add_argument(
        "--rednote-upload-on-ig-failure",
        action="store_true",
        help="Attempt Rednote upload even when Instagram upload is not explicitly confirmed.",
    )
    parser.add_argument(
        "--skip-rednote",
        action="store_true",
        help="Skip Rednote uploads even if config/env enables them.",
    )
    parser.add_argument(
        "--rednote-secrets-file",
        default="rednote_publish.local.env",
        help="Local env-style file for Rednote settings (default: rednote_publish.local.env).",
    )
    return parser.parse_args()


def _parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if not normalized:
        return default
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def load_env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        if not path.exists():
            return values
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("\ufeff"):
                line = line.lstrip("\ufeff").strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.lstrip("\ufeff").strip()
            if not key:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key] = value
    except Exception as e:
        print(f"[WARN] Failed to load env values from {path}: {e}")
    return values


def _resolve_facebook_join_prompt_mode() -> str:
    mode = str(getattr(config, "FACEBOOK_JOIN_PROMPT_MODE", "both") or "both").strip().lower()
    if mode not in {"off", "title", "comment", "both"}:
        mode = "both"
    return mode


def _resolve_facebook_join_prompt_text() -> str:
    return str(getattr(config, "FACEBOOK_JOIN_PROMPT_TEXT", "") or "").strip()


def _resolve_facebook_media_map_path() -> Path:
    raw_path = str(
        getattr(
            config,
            "FACEBOOK_MEDIA_GAME_MAP_PATH",
            "logs/webhook_services/facebook_media_game_mapping.json",
        )
        or "logs/webhook_services/facebook_media_game_mapping.json"
    ).strip()
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _resolve_youtube_media_map_path() -> Path:
    raw_path = str(
        getattr(
            config,
            "YOUTUBE_MEDIA_GAME_MAP_PATH",
            "logs/webhook_services/youtube_media_game_mapping.json",
        )
        or "logs/webhook_services/youtube_media_game_mapping.json"
    ).strip()
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _resolve_youtube_upload_join_comment_enabled() -> bool:
    return _parse_bool(
        os.getenv("YOUTUBE_UPLOAD_JOIN_COMMENT_ENABLED"),
        default=bool(getattr(config, "YOUTUBE_UPLOAD_JOIN_COMMENT_ENABLED", True)),
    )


def _resolve_youtube_upload_join_comment_text() -> str:
    return str(
        os.getenv("YOUTUBE_UPLOAD_JOIN_COMMENT_TEXT")
        or getattr(config, "YOUTUBE_UPLOAD_JOIN_COMMENT_TEXT", 'Comment "JOIN" in order to be added to future games')
        or ""
    ).strip()


def _resolve_youtube_comment_token_path() -> Path:
    raw_path = str(
        os.getenv("YOUTUBE_COMMENT_TOKEN_PATH")
        or getattr(config, "YOUTUBE_COMMENT_TOKEN_PATH", "secrets/youtube_comment_token.pickle")
        or "secrets/youtube_comment_token.pickle"
    ).strip()
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _resolve_youtube_upload_token_path() -> Path:
    raw_path = str(
        os.getenv("YOUTUBE_TOKEN_PATH")
        or getattr(config, "YOUTUBE_TOKEN_PATH", "secrets/youtube_token.json")
        or "secrets/youtube_token.json"
    ).strip()
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _resolve_snapchat_access_token_path(raw_value: str | None = None) -> Path:
    raw_path = str(
        raw_value
        or os.getenv("SNAPCHAT_ACCESS_TOKEN_PATH")
        or getattr(config, "SNAPCHAT_ACCESS_TOKEN_PATH", "secrets/snapchat_access_token.json")
        or "secrets/snapchat_access_token.json"
    ).strip()
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _resolve_snapchat_refresh_token_path(raw_value: str | None = None) -> Path:
    raw_path = str(
        raw_value
        or os.getenv("SNAPCHAT_REFRESH_TOKEN_PATH")
        or getattr(config, "SNAPCHAT_REFRESH_TOKEN_PATH", "secrets/snapchat_refresh_token.json")
        or "secrets/snapchat_refresh_token.json"
    ).strip()
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _youtube_comment_required_scopes() -> list[str]:
    return ["https://www.googleapis.com/auth/youtube.force-ssl"]


def _import_youtube_comment_libs():
    global _YOUTUBE_COMMENT_LIBS, _YOUTUBE_COMMENT_LIBS_FAILED
    if _YOUTUBE_COMMENT_LIBS is not None:
        return _YOUTUBE_COMMENT_LIBS
    if _YOUTUBE_COMMENT_LIBS_FAILED:
        return None
    try:
        import pickle
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        _YOUTUBE_COMMENT_LIBS = {
            "pickle": pickle,
            "build": build,
            "Request": Request,
        }
        return _YOUTUBE_COMMENT_LIBS
    except Exception as exc:
        print(f"[WARN] YouTube API libraries unavailable for upload comment posting: {exc}")
        _YOUTUBE_COMMENT_LIBS_FAILED = True
        return None


def _load_pickled_youtube_credentials(path: Path):
    libs = _import_youtube_comment_libs()
    if libs is None or not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            return libs["pickle"].load(handle)
    except Exception as exc:
        print(f"[WARN] Failed to load YouTube credentials from {path}: {exc}")
        return None


def _save_pickled_youtube_credentials(path: Path, creds):
    libs = _import_youtube_comment_libs()
    if libs is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            libs["pickle"].dump(creds, handle)
    except Exception as exc:
        print(f"[WARN] Failed to save YouTube credentials to {path}: {exc}")


def _credentials_include_required_scopes(creds, required_scopes: list[str]) -> bool:
    if creds is None:
        return False
    scopes = getattr(creds, "scopes", None)
    if not scopes:
        # Some token objects do not expose scopes directly; let API call validate.
        return True
    current = {str(scope).strip() for scope in scopes if str(scope).strip()}
    required = {str(scope).strip() for scope in required_scopes if str(scope).strip()}
    return required.issubset(current)


def _get_youtube_comment_client():
    global _YOUTUBE_COMMENT_CLIENT
    with _YOUTUBE_COMMENT_CLIENT_LOCK:
        if _YOUTUBE_COMMENT_CLIENT is not None:
            return _YOUTUBE_COMMENT_CLIENT
        libs = _import_youtube_comment_libs()
        if libs is None:
            return None

        required_scopes = _youtube_comment_required_scopes()
        token_candidates: list[Path] = []
        for candidate in (_resolve_youtube_comment_token_path(), _resolve_youtube_upload_token_path()):
            if candidate and candidate not in token_candidates:
                token_candidates.append(candidate)

        creds = None
        source_path = None
        for candidate in token_candidates:
            loaded = _load_pickled_youtube_credentials(candidate)
            if loaded is None:
                continue
            if _credentials_include_required_scopes(loaded, required_scopes):
                creds = loaded
                source_path = candidate
                break
            if creds is None:
                creds = loaded
                source_path = candidate

        if creds is None:
            print(
                "[WARN] YouTube JOIN upload-comment skipped: no OAuth token found. "
                f"Expected one of: {', '.join(str(p) for p in token_candidates)}"
            )
            return None

        if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            try:
                creds.refresh(libs["Request"]())
                if source_path:
                    _save_pickled_youtube_credentials(source_path, creds)
            except Exception as exc:
                print(f"[WARN] Failed to refresh YouTube OAuth token for upload comment: {exc}")
                return None

        if not _credentials_include_required_scopes(creds, required_scopes):
            print(
                "[WARN] YouTube JOIN upload-comment skipped: token missing scope "
                f"{required_scopes}. Re-auth comment token with that scope."
            )
            return None

        try:
            _YOUTUBE_COMMENT_CLIENT = libs["build"](
                "youtube",
                "v3",
                credentials=creds,
                cache_discovery=False,
            )
        except Exception as exc:
            print(f"[WARN] Failed to create YouTube client for upload comments: {exc}")
            _YOUTUBE_COMMENT_CLIENT = None
        return _YOUTUBE_COMMENT_CLIENT


def post_youtube_comment(video_id: str, message: str) -> bool:
    video_ref = str(video_id or "").strip()
    payload_text = str(message or "").strip()
    if not video_ref or not payload_text:
        return False
    youtube = _get_youtube_comment_client()
    if youtube is None:
        return False
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_ref,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": payload_text,
                        }
                    },
                }
            },
        ).execute()
        return True
    except Exception as exc:
        print(f"[WARN] YouTube JOIN upload-comment request failed for {video_ref}: {exc}")
        return False


def fetch_facebook_object_metadata(object_id: str, access_token: str, api_version: str = "v18.0") -> dict:
    if not object_id:
        return {}
    version = str(api_version or "v18.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{version}/{object_id}"
    fields = "id,post_id,permalink_url,title,description,message,created_time"
    try:
        response = requests.get(
            url,
            params={"fields": fields, "access_token": access_token},
            timeout=(15, 45),
        )
    except Exception as exc:
        print(f"[WARN] FB metadata fetch failed for {object_id}: {exc}")
        return {}

    if not response.ok:
        print(f"[WARN] FB metadata fetch failed for {object_id}: HTTP {response.status_code} {response.text[:400]}")
        return {}

    try:
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def post_facebook_comment(target_id: str, message: str, access_token: str, api_version: str = "v18.0") -> bool:
    if not target_id or not message:
        return False
    version = str(api_version or "v18.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{version}/{target_id}/comments"
    payload = {
        "message": message,
        "access_token": access_token,
    }
    try:
        response = requests.post(url, data=payload, timeout=(15, 90))
    except Exception as exc:
        print(f"[WARN] FB CTA comment request failed for target {target_id}: {exc}")
        return False
    if response.ok:
        return True
    print(
        f"[WARN] FB CTA comment failed for target {target_id}: "
        f"HTTP {response.status_code} {response.text[:400]}"
    )
    return False


def load_export_password_from_file(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_run_context(path: Path | None) -> dict | None:
    if not path:
        return None
    try:
        if not path.exists():
            print(f"[WARN] Run context not found: {path}")
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception as e:
        print(f"[WARN] Failed to load run context {path}: {e}")
        return None


def find_latest_run_context(day_number: int | None = None) -> Path | None:
    log_dir = PROJECT_ROOT / "logs" / "scheduled_upload"
    if not log_dir.exists():
        return None
    candidates = sorted(
        log_dir.glob("run_context_day_*.json"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
        reverse=True,
    )
    if day_number is None:
        return candidates[0] if candidates else None

    day_value = int(day_number)
    fallback = None
    for candidate in candidates:
        if fallback is None:
            fallback = candidate
        payload = load_run_context(candidate)
        if not isinstance(payload, dict):
            continue
        try:
            if int(payload.get("day_number")) == day_value:
                return candidate
        except Exception:
            continue
    return fallback


def _clear_api_caches() -> None:
    try:
        load_day_summary.cache_clear()
    except Exception:
        pass
    try:
        load_game_results.cache_clear()
    except Exception:
        pass


def _extract_top_usernames_from_payload(game_payload: dict | None, limit: int = 10) -> list[str]:
    if not isinstance(game_payload, dict):
        return []
    results = game_payload.get("results", []) or []
    if not isinstance(results, list):
        return []
    sorted_results = sorted(
        (entry for entry in results if isinstance(entry, dict)),
        key=lambda entry: entry.get("placement", entry.get("rank", 0) or 0),
    )
    usernames: list[str] = []
    for entry in sorted_results:
        username = entry.get("username")
        if not username:
            continue
        usernames.append(str(username))
        if len(usernames) >= limit:
            break
    return usernames


def _payload_matches_ready_requirements(
    payload: dict | None,
    *,
    min_timestamp: str = "",
) -> bool:
    if not isinstance(payload, dict):
        return False
    game_id = str(payload.get("game_id") or "").strip()
    timestamp = str(payload.get("timestamp") or "").strip()
    results = payload.get("results")
    if not game_id or not timestamp or not isinstance(results, list) or not results:
        return False
    if min_timestamp and timestamp < min_timestamp:
        return False
    return True


def _load_latest_game_from_api(
    day_number: int,
    game_mode: str,
    *,
    min_timestamp: str = "",
    refresh: bool = False,
) -> dict | None:
    if refresh:
        _clear_api_caches()
    day_data = load_day_summary(day_number)
    if not day_data:
        return None
    games = [
        game for game in (day_data.get("games", []) or [])
        if isinstance(game, dict) and game.get("game_type") == game_mode
    ]
    if min_timestamp:
        games = [game for game in games if str(game.get("timestamp") or "").strip() >= min_timestamp]
    if not games:
        return None
    game_summary = max(games, key=lambda game: str(game.get("timestamp", "")))
    game_id = str(game_summary.get("game_id") or "").strip()
    if not game_id:
        return None
    payload = load_game_results(game_id)
    return payload if _payload_matches_ready_requirements(payload, min_timestamp=min_timestamp) else None


def _load_latest_game_from_events(
    day_number: int,
    game_mode: str,
    *,
    min_timestamp: str = "",
    scan_max_files: int = 12,
) -> dict | None:
    events_dir = PROJECT_ROOT / "backups" / "game_results" / "events"
    if not events_dir.exists():
        return None
    try:
        files = sorted(
            events_dir.rglob("*.ndjson"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0.0,
            reverse=True,
        )
    except Exception:
        return None

    if scan_max_files > 0:
        files = files[:scan_max_files]

    best_payload = None
    best_timestamp = ""
    for path in files:
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(payload, dict):
                        continue
                    if payload.get("day_number") != day_number or payload.get("game_type") != game_mode:
                        continue
                    timestamp = str(payload.get("timestamp") or "").strip()
                    if min_timestamp and timestamp < min_timestamp:
                        continue
                    if not _payload_matches_ready_requirements(payload, min_timestamp=min_timestamp):
                        continue
                    if best_payload is None or timestamp > best_timestamp:
                        best_payload = payload
                        best_timestamp = timestamp
        except Exception:
            continue
    return best_payload


def load_latest_game_payload_for_upload(
    day_number: int,
    game_mode: str,
    *,
    min_timestamp: str = "",
    prefer_events: bool = False,
    refresh_api: bool = False,
    events_scan_max_files: int = 12,
) -> dict | None:
    event_payload = _load_latest_game_from_events(
        day_number,
        game_mode,
        min_timestamp=min_timestamp,
        scan_max_files=events_scan_max_files,
    )
    api_payload = _load_latest_game_from_api(
        day_number,
        game_mode,
        min_timestamp=min_timestamp,
        refresh=refresh_api,
    )

    if prefer_events:
        return event_payload or api_payload
    if api_payload and event_payload:
        api_ts = str(api_payload.get("timestamp") or "")
        event_ts = str(event_payload.get("timestamp") or "")
        return api_payload if api_ts >= event_ts else event_payload
    return api_payload or event_payload


def wait_for_game_payload(
    day_number: int,
    game_mode: str,
    *,
    max_seconds: int,
    poll_seconds: int,
    min_timestamp: str = "",
    prefer_events: bool = False,
    events_scan_max_files: int = 12,
) -> dict | None:
    start = time.time()
    while True:
        payload = load_latest_game_payload_for_upload(
            day_number,
            game_mode,
            min_timestamp=min_timestamp,
            prefer_events=prefer_events,
            refresh_api=True,
            events_scan_max_files=events_scan_max_files,
        )
        if payload is not None:
            return payload
        if max_seconds == 0:
            return None
        elapsed = time.time() - start
        if max_seconds > 0 and elapsed >= max_seconds:
            return None
        time.sleep(max(1, poll_seconds))

def run_ig_export(ig_persistent, args):
    if args.ig_uploader != "safe" or not ig_persistent:
        print("IG export requires --ig-uploader safe; skipping export.")
        return False

    profile_name = args.ig_export_profile or getattr(config, "IG_EXPORT_PROFILE_NAME", "followerbattlegrounds")
    account_center_url = getattr(config, "IG_EXPORT_ACCOUNT_CENTER_URL", "https://accountscenter.instagram.com/")
    info_permissions_label = getattr(config, "IG_EXPORT_INFO_PERMISSIONS_LABEL", "Your information and permissions")
    export_info_label = getattr(config, "IG_EXPORT_EXPORT_INFO_LABEL", "Export your information")
    export_to_device_label = getattr(config, "IG_EXPORT_EXPORT_TO_DEVICE_LABEL", "Export to device")
    date_range_label = args.ig_export_date_range or getattr(config, "IG_EXPORT_DATE_RANGE", "Last week")
    followers_label = getattr(config, "IG_EXPORT_FOLLOWERS_LABEL", "Followers and following")
    format_label = getattr(config, "IG_EXPORT_FORMAT_LABEL", "JSON")
    media_quality_label = getattr(config, "IG_EXPORT_MEDIA_QUALITY_LABEL", "Low")
    wait_for_ready = getattr(config, "IG_EXPORT_WAIT_FOR_READY", True)
    max_wait_minutes = getattr(config, "IG_EXPORT_MAX_WAIT_MINUTES", 90)
    poll_interval_seconds = getattr(config, "IG_EXPORT_POLL_INTERVAL_SECONDS", 60)
    export_password = getattr(config, "IG_EXPORT_PASSWORD", "") or os.getenv("IG_EXPORT_PASSWORD", "")
    if not export_password:
        export_password = load_export_password_from_file(Path("ig_export_password.txt"))

    return ig_persistent.export_followers_from_account_center(
        profile_name=profile_name,
        account_center_url=account_center_url,
        info_permissions_label=info_permissions_label,
        export_info_label=export_info_label,
        export_to_device_label=export_to_device_label,
        date_range_label=date_range_label,
        followers_label=followers_label,
        format_label=format_label,
        media_quality_label=media_quality_label,
        export_password=export_password,
        wait_for_ready=wait_for_ready,
        max_wait_minutes=max_wait_minutes,
        poll_interval_seconds=poll_interval_seconds,
    )


def main():
    args = parse_args()
    if args.upload_interval_minutes is not None:
        if args.upload_interval_minutes <= 0:
            raise SystemExit("--upload-interval-minutes must be > 0")
        args.delay_seconds = None
        args.delay_min_seconds = None
        args.delay_max_seconds = None

    if args.pre_upload_wait_minutes is not None:
        if args.pre_upload_wait_minutes < 0:
            raise SystemExit("--pre-upload-wait-minutes must be >= 0")
        args.pre_upload_wait_seconds = args.pre_upload_wait_minutes * 60
    elif args.pre_upload_wait_seconds < 0:
        raise SystemExit("--pre-upload-wait-seconds must be >= 0")

    if args.ready_grace_minutes is not None:
        if args.ready_grace_minutes < 0:
            raise SystemExit("--ready-grace-minutes must be >= 0")
        args.ready_grace_seconds = args.ready_grace_minutes * 60
    elif args.ready_grace_seconds < 0:
        raise SystemExit("--ready-grace-seconds must be >= 0")

    if args.wait_poll_minutes is not None:
        if args.wait_poll_minutes <= 0:
            raise SystemExit("--wait-poll-minutes must be > 0")
        args.wait_poll_seconds = args.wait_poll_minutes * 60

    if args.wait_forever:
        args.wait_for_videos = True
        args.wait_max_seconds = -1

    if args.queue_ready_videos:
        args.wait_for_videos = True
        if args.wait_max_seconds == 0:
            args.wait_max_seconds = -1
        if args.ready_grace_seconds == 0:
            args.ready_grace_seconds = 6 * 60
        if not args.skip_stats:
            raise SystemExit("--queue-ready-videos requires --skip-stats while the render run is still in progress.")

    if args.events_scan_max_files < 0:
        raise SystemExit("--events-scan-max-files must be >= 0")

    if args.ig_export_after_uploads and not args.ig_export_followers:
        args.ig_export_followers = True

    if args.export_only:
        if args.ig_uploader != "safe":
            raise SystemExit("Export-only requires --ig-uploader safe.")
        ig_cookies_path = Path(os.getenv("IG_COOKIES_FILE", str(args.ig_cookies_file)))
        from persistent_instagram_uploader import PersistentInstagramUploader
        export_download_dir = getattr(config, "IG_EXPORT_DOWNLOAD_DIR", "")
        ig_persistent = PersistentInstagramUploader(
            cookies_file=str(ig_cookies_path),
            headless=args.ig_headless,
            download_dir=export_download_dir or None,
        )
        if not ig_persistent.start_session():
            raise SystemExit("Failed to start persistent Instagram session.")
        try:
            ok = run_ig_export(ig_persistent, args)
            if not ok:
                raise SystemExit("Export failed.")
        finally:
            ig_persistent.close_session()
        print("Export completed.")
        return

    resolved_run_context_path = args.run_context_file
    if args.queue_ready_videos and resolved_run_context_path is None:
        requested_day = (
            int(args.run_day_number)
            if args.run_day_number is not None
            else int(getattr(config, "DAY_NUMBER", 0) or 0)
        )
        resolved_run_context_path = find_latest_run_context(requested_day if requested_day > 0 else None)
        if resolved_run_context_path is None:
            raise SystemExit(
                "--queue-ready-videos could not find a run context. Pass --run-context-file or rerun main.py after this patch."
            )
        print(f"[INFO] Using latest run context: {resolved_run_context_path}")

    run_context = load_run_context(resolved_run_context_path)
    run_day_number = (
        args.run_day_number
        if args.run_day_number is not None
        else (run_context.get("day_number") if run_context else None)
    )
    if run_day_number is None:
        run_day_number = getattr(config, "DAY_NUMBER", 0)
    run_platform_target = normalize_platform_target(
        (run_context.get("platform_target") if run_context else None) or getattr(config, "PLATFORM_TARGET", "instagram")
    )
    run_game_modes = (run_context.get("all_game_modes") if run_context else None) or getattr(config, "ALL_GAME_MODES", [])
    if not run_game_modes:
        fallback_mode = getattr(config, "GAME_MODE", "")
        run_game_modes = [fallback_mode] if fallback_mode else []

    if args.queue_ready_videos and run_context is None:
        raise SystemExit("--queue-ready-videos requires a valid run context.")

    run_context_timestamp = str((run_context or {}).get("timestamp") or "").strip()
    run_context_min_epoch = _iso_timestamp_to_epoch(run_context_timestamp)

    if run_context:
        print(
            f"[INFO] Using run context: day {run_day_number}, modes {len(run_game_modes)}, "
            f"platform={run_platform_target}"
        )
    if args.queue_ready_videos:
        print(
            "[INFO] Queue-ready mode enabled: waiting for fresh video files and per-game event data "
            "before each upload."
        )

    fb_secrets_path = Path(args.facebook_secrets_file)
    fb_local_env = load_env_values(fb_secrets_path)
    fb_page_id = (
        args.facebook_page_id
        or os.getenv("FACEBOOK_PAGE_ID")
        or fb_local_env.get("FACEBOOK_PAGE_ID")
        or getattr(config, "FACEBOOK_PAGE_ID", "")
    ).strip()
    fb_access_token = (
        args.facebook_access_token
        or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        or fb_local_env.get("FACEBOOK_PAGE_ACCESS_TOKEN")
        or getattr(config, "FACEBOOK_PAGE_ACCESS_TOKEN", "")
    ).strip()
    fb_api_version = (
        args.facebook_api_version
        or os.getenv("FACEBOOK_GRAPH_API_VERSION")
        or fb_local_env.get("FACEBOOK_GRAPH_API_VERSION")
        or getattr(config, "FACEBOOK_GRAPH_API_VERSION", "v18.0")
    ).strip() or "v18.0"
    fb_auto_upload_env = os.getenv("FACEBOOK_PAGE_AUTO_UPLOAD")
    if fb_auto_upload_env is not None:
        fb_auto_upload = _parse_bool(fb_auto_upload_env, default=False)
    elif "FACEBOOK_PAGE_AUTO_UPLOAD" in fb_local_env:
        fb_auto_upload = _parse_bool(fb_local_env.get("FACEBOOK_PAGE_AUTO_UPLOAD"), default=False)
    else:
        fb_auto_upload = bool(getattr(config, "FACEBOOK_PAGE_AUTO_UPLOAD", False))
    fb_upload_enabled = bool(args.enable_facebook_page_upload or fb_auto_upload)
    fb_upload_on_ig_failure = bool(args.facebook_upload_on_ig_failure)
    if not fb_upload_on_ig_failure:
        fb_on_fail_env = os.getenv("FACEBOOK_UPLOAD_ON_IG_FAILURE")
        if fb_on_fail_env is not None:
            fb_upload_on_ig_failure = _parse_bool(fb_on_fail_env, default=False)
        elif "FACEBOOK_UPLOAD_ON_IG_FAILURE" in fb_local_env:
            fb_upload_on_ig_failure = _parse_bool(
                fb_local_env.get("FACEBOOK_UPLOAD_ON_IG_FAILURE"),
                default=False,
            )
        else:
            fb_upload_on_ig_failure = bool(getattr(config, "FACEBOOK_UPLOAD_ON_IG_FAILURE", False))
    if fb_upload_enabled and (not fb_page_id or not fb_access_token):
        print(
            f"[WARN] FB page upload enabled but missing credentials. Set FACEBOOK_PAGE_ID and "
            f"FACEBOOK_PAGE_ACCESS_TOKEN via args, env, or {fb_secrets_path}."
        )
        fb_upload_enabled = False
    if fb_upload_enabled:
        if fb_upload_on_ig_failure:
            print(f"[INFO] FB page upload enabled (will upload even if IG confirmation is missing): {fb_page_id}")
        else:
            print(f"[INFO] FB page upload enabled (requires IG success): {fb_page_id}")

    snap_secrets_path = Path(args.snapchat_secrets_file)
    snap_local_env = load_env_values(snap_secrets_path)
    snap_client_id = (
        args.snapchat_client_id
        or os.getenv("SNAPCHAT_CLIENT_ID")
        or snap_local_env.get("SNAPCHAT_CLIENT_ID")
        or getattr(config, "SNAPCHAT_CLIENT_ID", "")
    ).strip()
    snap_client_secret = (
        args.snapchat_client_secret
        or os.getenv("SNAPCHAT_CLIENT_SECRET")
        or snap_local_env.get("SNAPCHAT_CLIENT_SECRET")
        or getattr(config, "SNAPCHAT_CLIENT_SECRET", "")
    ).strip()
    snap_redirect_uri = (
        args.snapchat_redirect_uri
        or os.getenv("SNAPCHAT_REDIRECT_URI")
        or snap_local_env.get("SNAPCHAT_REDIRECT_URI")
        or getattr(config, "SNAPCHAT_REDIRECT_URI", "")
    ).strip()
    snap_profile_id = (
        args.snapchat_profile_id
        or os.getenv("SNAPCHAT_PROFILE_ID")
        or snap_local_env.get("SNAPCHAT_PROFILE_ID")
        or getattr(config, "SNAPCHAT_PROFILE_ID", "")
    ).strip()
    snap_scope = (
        os.getenv("SNAPCHAT_SCOPE")
        or snap_local_env.get("SNAPCHAT_SCOPE")
        or getattr(config, "SNAPCHAT_SCOPE", "snapchat-profile-api")
        or "snapchat-profile-api"
    ).strip() or "snapchat-profile-api"
    snap_api_base = (
        os.getenv("SNAPCHAT_API_BASE")
        or snap_local_env.get("SNAPCHAT_API_BASE")
        or getattr(config, "SNAPCHAT_API_BASE", "https://businessapi.snapchat.com")
        or "https://businessapi.snapchat.com"
    ).strip() or "https://businessapi.snapchat.com"
    snap_access_token_path = _resolve_snapchat_access_token_path(
        raw_value=snap_local_env.get("SNAPCHAT_ACCESS_TOKEN_PATH"),
    )
    snap_refresh_token_path = _resolve_snapchat_refresh_token_path(
        raw_value=snap_local_env.get("SNAPCHAT_REFRESH_TOKEN_PATH"),
    )

    snap_enable_env = os.getenv("SNAPCHAT_ENABLE")
    if snap_enable_env is not None:
        snap_feature_enabled = _parse_bool(snap_enable_env, default=True)
    elif "SNAPCHAT_ENABLE" in snap_local_env:
        snap_feature_enabled = _parse_bool(
            snap_local_env.get("SNAPCHAT_ENABLE"),
            default=bool(getattr(config, "SNAPCHAT_ENABLE", True)),
        )
    else:
        snap_feature_enabled = bool(getattr(config, "SNAPCHAT_ENABLE", True))

    snap_auto_upload_env = os.getenv("SNAPCHAT_AUTO_UPLOAD")
    if snap_auto_upload_env is not None:
        snap_auto_upload = _parse_bool(snap_auto_upload_env, default=False)
    elif "SNAPCHAT_AUTO_UPLOAD" in snap_local_env:
        snap_auto_upload = _parse_bool(
            snap_local_env.get("SNAPCHAT_AUTO_UPLOAD"),
            default=bool(getattr(config, "SNAPCHAT_AUTO_UPLOAD", False)),
        )
    else:
        snap_auto_upload = bool(getattr(config, "SNAPCHAT_AUTO_UPLOAD", False))

    snap_upload_enabled = bool(snap_feature_enabled and (args.enable_snapchat_upload or snap_auto_upload))
    if args.skip_snapchat:
        snap_upload_enabled = False

    snap_on_fail_env = os.getenv("SNAPCHAT_UPLOAD_ON_IG_FAILURE")
    if args.snapchat_upload_on_ig_failure:
        snap_upload_on_ig_failure = True
    elif snap_on_fail_env is not None:
        snap_upload_on_ig_failure = _parse_bool(snap_on_fail_env, default=False)
    elif "SNAPCHAT_UPLOAD_ON_IG_FAILURE" in snap_local_env:
        snap_upload_on_ig_failure = _parse_bool(
            snap_local_env.get("SNAPCHAT_UPLOAD_ON_IG_FAILURE"),
            default=bool(getattr(config, "SNAPCHAT_UPLOAD_ON_IG_FAILURE", False)),
        )
    else:
        snap_upload_on_ig_failure = bool(getattr(config, "SNAPCHAT_UPLOAD_ON_IG_FAILURE", False))

    snap_story_enabled = _parse_bool(
        os.getenv("SNAPCHAT_ENABLE_STORY_POST", snap_local_env.get("SNAPCHAT_ENABLE_STORY_POST")),
        default=bool(getattr(config, "SNAPCHAT_ENABLE_STORY_POST", True)),
    )
    snap_spotlight_enabled = _parse_bool(
        os.getenv("SNAPCHAT_ENABLE_SPOTLIGHT_POST", snap_local_env.get("SNAPCHAT_ENABLE_SPOTLIGHT_POST")),
        default=bool(getattr(config, "SNAPCHAT_ENABLE_SPOTLIGHT_POST", True)),
    )
    snap_spotlight_locale = str(
        os.getenv("SNAPCHAT_SPOTLIGHT_LOCALE")
        or snap_local_env.get("SNAPCHAT_SPOTLIGHT_LOCALE")
        or getattr(config, "SNAPCHAT_SPOTLIGHT_LOCALE", "en_US")
        or "en_US"
    ).strip() or "en_US"
    snap_spotlight_skip_save = _parse_bool(
        os.getenv("SNAPCHAT_SPOTLIGHT_SKIP_SAVE_TO_PROFILE", snap_local_env.get("SNAPCHAT_SPOTLIGHT_SKIP_SAVE_TO_PROFILE")),
        default=bool(getattr(config, "SNAPCHAT_SPOTLIGHT_SKIP_SAVE_TO_PROFILE", False)),
    )
    snap_use_non_ig_variant = _parse_bool(
        os.getenv("SNAPCHAT_USE_NON_IG_VARIANT", snap_local_env.get("SNAPCHAT_USE_NON_IG_VARIANT")),
        default=bool(getattr(config, "SNAPCHAT_USE_NON_IG_VARIANT", True)),
    )
    snap_retry_count = _coerce_int(
        os.getenv("SNAPCHAT_RETRY_COUNT") or snap_local_env.get("SNAPCHAT_RETRY_COUNT") or getattr(config, "SNAPCHAT_RETRY_COUNT", 3),
        3,
    )
    snap_timeout_seconds = _coerce_int(
        os.getenv("SNAPCHAT_TIMEOUT_SECONDS") or snap_local_env.get("SNAPCHAT_TIMEOUT_SECONDS") or getattr(config, "SNAPCHAT_TIMEOUT_SECONDS", 120),
        120,
    )
    snap_uploader = str(
        args.snapchat_uploader
        or os.getenv("SNAPCHAT_UPLOADER")
        or snap_local_env.get("SNAPCHAT_UPLOADER")
        or getattr(config, "SNAPCHAT_UPLOADER", "safe")
        or "safe"
    ).strip().lower()
    if snap_uploader not in {"api", "safe"}:
        snap_uploader = "safe"
    snap_cookies_path = Path(
        os.getenv("SNAPCHAT_COOKIES_FILE")
        or snap_local_env.get("SNAPCHAT_COOKIES_FILE")
        or str(args.snapchat_cookies_file)
    )
    snap_profile_dir = str(
        os.getenv("SNAPCHAT_PROFILE_DIR")
        or snap_local_env.get("SNAPCHAT_PROFILE_DIR")
        or args.snapchat_profile_dir
        or getattr(config, "SNAPCHAT_PROFILE_DIR", "sessions/snapchat_chrome_profile")
        or ""
    ).strip()
    snap_headless = bool(
        args.snapchat_headless
        or _parse_bool(
            os.getenv("SNAPCHAT_HEADLESS", snap_local_env.get("SNAPCHAT_HEADLESS")),
            default=bool(getattr(config, "SNAPCHAT_HEADLESS", False)),
        )
    )
    snap_safe_spotlight_only = _parse_bool(
        os.getenv("SNAPCHAT_SAFE_SPOTLIGHT_ONLY", snap_local_env.get("SNAPCHAT_SAFE_SPOTLIGHT_ONLY")),
        default=bool(getattr(config, "SNAPCHAT_SAFE_SPOTLIGHT_ONLY", True)),
    )

    if args.snapchat_save_cookies:
        if SafeSnapchatUploader is None:
            raise SystemExit("safe_snapchat_uploader is unavailable. Ensure selenium is installed.")
        snap_cookie_helper = SafeSnapchatUploader(
            cookies_file=str(snap_cookies_path),
            headless=snap_headless,
            spotlight_only=snap_safe_spotlight_only,
            profile_dir=snap_profile_dir,
        )
        ok = snap_cookie_helper.save_cookies()
        raise SystemExit(0 if ok else 1)

    if args.snapchat_print_auth_url or args.snapchat_auth_code:
        if build_snapchat_authorize_url is None or exchange_snapchat_code_for_tokens is None or write_snapchat_token_payload is None:
            raise SystemExit("Snapchat helper is unavailable. Ensure shared/snapchat_uploader.py imports successfully.")
        if not snap_client_id or not snap_redirect_uri:
            raise SystemExit("Snapchat auth helper needs SNAPCHAT_CLIENT_ID and SNAPCHAT_REDIRECT_URI.")
        if args.snapchat_print_auth_url:
            auth_url = build_snapchat_authorize_url(
                client_id=snap_client_id,
                redirect_uri=snap_redirect_uri,
                scope=snap_scope,
                state=args.snapchat_auth_state,
            )
            print("Snapchat authorize URL:")
            print(auth_url)
        auth_code = str(args.snapchat_auth_code or "").strip()
        if auth_code:
            if not snap_client_secret:
                raise SystemExit("Snapchat token exchange needs SNAPCHAT_CLIENT_SECRET.")
            token_payload = exchange_snapchat_code_for_tokens(
                client_id=snap_client_id,
                client_secret=snap_client_secret,
                redirect_uri=snap_redirect_uri,
                auth_code=auth_code,
            )
            write_snapchat_token_payload(
                access_token_path=snap_access_token_path,
                refresh_token_path=snap_refresh_token_path,
                token_payload=token_payload,
            )
            print(f"[OK] Snapchat tokens saved: {snap_access_token_path}")
        return

    if snap_upload_enabled and snap_uploader == "api" and upload_snapchat is None:
        print("[WARN] Snapchat API upload enabled, but shared.snapchat_uploader is unavailable.")
        snap_upload_enabled = False
    if snap_upload_enabled and snap_uploader == "safe" and SafeSnapchatUploader is None:
        print("[WARN] Snapchat safe upload enabled, but safe_snapchat_uploader is unavailable.")
        snap_upload_enabled = False

    if snap_upload_enabled:
        if snap_uploader == "api":
            missing_fields = []
            if not snap_profile_id:
                missing_fields.append("SNAPCHAT_PROFILE_ID")
            if not snap_client_id:
                missing_fields.append("SNAPCHAT_CLIENT_ID")
            if not snap_client_secret:
                missing_fields.append("SNAPCHAT_CLIENT_SECRET")
            if not snap_redirect_uri:
                missing_fields.append("SNAPCHAT_REDIRECT_URI")
            if missing_fields:
                print(
                    "[WARN] Snapchat API upload enabled but missing required settings: "
                    + ", ".join(missing_fields)
                    + f". Provide via args, env, or {snap_secrets_path}."
                )
                snap_upload_enabled = False
            elif not snap_access_token_path.exists() and not snap_refresh_token_path.exists():
                print(
                    "[WARN] Snapchat API upload enabled but token files are missing. "
                    "Run --snapchat-print-auth-url and --snapchat-auth-code first."
                )
                snap_upload_enabled = False
        else:
            if not snap_cookies_path.exists() and not snap_profile_dir:
                print(
                    f"[WARN] Snapchat safe upload enabled but cookie file is missing: {snap_cookies_path}. "
                    "Run with --snapchat-save-cookies first, or configure --snapchat-profile-dir."
                )
                snap_upload_enabled = False

    if snap_upload_enabled:
        if snap_upload_on_ig_failure:
            print(
                "[INFO] Snapchat upload enabled (will upload even if IG confirmation is missing): "
                f"{'profile=' + snap_profile_id if snap_uploader == 'api' else 'safe_session'}"
            )
        else:
            print(
                "[INFO] Snapchat upload enabled (requires IG success): "
                f"{'profile=' + snap_profile_id if snap_uploader == 'api' else 'safe_session'}"
            )
        if snap_uploader == "safe":
            print(
                f"[INFO] Snapchat settings: uploader=safe, cookies={snap_cookies_path}, "
                f"profile_dir={snap_profile_dir or '-'}, headless={snap_headless}, spotlight_only={snap_safe_spotlight_only}, "
                f"use_non_ig_variant={snap_use_non_ig_variant}"
            )
        else:
            print(
                f"[INFO] Snapchat settings: uploader=api, story={snap_story_enabled}, "
                f"spotlight={snap_spotlight_enabled}, locale={snap_spotlight_locale}, "
                f"use_non_ig_variant={snap_use_non_ig_variant}"
            )

    x_secrets_path = Path(args.x_secrets_file)
    x_local_env = load_env_values(x_secrets_path)
    x_consumer_key = (
        args.x_consumer_key
        or os.getenv("X_CONSUMER_KEY")
        or x_local_env.get("X_CONSUMER_KEY")
        or getattr(config, "X_CONSUMER_KEY", "")
    ).strip()
    x_consumer_secret = (
        args.x_consumer_secret
        or os.getenv("X_CONSUMER_SECRET")
        or x_local_env.get("X_CONSUMER_SECRET")
        or getattr(config, "X_CONSUMER_SECRET", "")
    ).strip()
    x_access_token = (
        args.x_access_token
        or os.getenv("X_ACCESS_TOKEN")
        or x_local_env.get("X_ACCESS_TOKEN")
        or getattr(config, "X_ACCESS_TOKEN", "")
    ).strip()
    x_access_token_secret = (
        args.x_access_token_secret
        or os.getenv("X_ACCESS_TOKEN_SECRET")
        or x_local_env.get("X_ACCESS_TOKEN_SECRET")
        or getattr(config, "X_ACCESS_TOKEN_SECRET", "")
    ).strip()
    x_upload_api_url = (
        os.getenv("X_UPLOAD_API_URL")
        or x_local_env.get("X_UPLOAD_API_URL")
        or getattr(config, "X_UPLOAD_API_URL", "https://upload.twitter.com/1.1/media/upload.json")
        or "https://upload.twitter.com/1.1/media/upload.json"
    ).strip() or "https://upload.twitter.com/1.1/media/upload.json"
    x_api_base = (
        os.getenv("X_API_BASE")
        or x_local_env.get("X_API_BASE")
        or getattr(config, "X_API_BASE", "https://api.x.com")
        or "https://api.x.com"
    ).strip() or "https://api.x.com"

    x_enable_env = os.getenv("X_ENABLE")
    if x_enable_env is not None:
        x_feature_enabled = _parse_bool(x_enable_env, default=True)
    elif "X_ENABLE" in x_local_env:
        x_feature_enabled = _parse_bool(
            x_local_env.get("X_ENABLE"),
            default=bool(getattr(config, "X_ENABLE", True)),
        )
    else:
        x_feature_enabled = bool(getattr(config, "X_ENABLE", True))

    x_auto_upload_env = os.getenv("X_AUTO_UPLOAD")
    if x_auto_upload_env is not None:
        x_auto_upload = _parse_bool(x_auto_upload_env, default=False)
    elif "X_AUTO_UPLOAD" in x_local_env:
        x_auto_upload = _parse_bool(
            x_local_env.get("X_AUTO_UPLOAD"),
            default=bool(getattr(config, "X_AUTO_UPLOAD", False)),
        )
    else:
        x_auto_upload = bool(getattr(config, "X_AUTO_UPLOAD", False))

    x_upload_enabled = bool(x_feature_enabled and (args.enable_x_upload or x_auto_upload))
    if args.skip_x:
        x_upload_enabled = False

    x_on_fail_env = os.getenv("X_UPLOAD_ON_IG_FAILURE")
    if args.x_upload_on_ig_failure:
        x_upload_on_ig_failure = True
    elif x_on_fail_env is not None:
        x_upload_on_ig_failure = _parse_bool(x_on_fail_env, default=False)
    elif "X_UPLOAD_ON_IG_FAILURE" in x_local_env:
        x_upload_on_ig_failure = _parse_bool(
            x_local_env.get("X_UPLOAD_ON_IG_FAILURE"),
            default=bool(getattr(config, "X_UPLOAD_ON_IG_FAILURE", False)),
        )
    else:
        x_upload_on_ig_failure = bool(getattr(config, "X_UPLOAD_ON_IG_FAILURE", False))

    x_order_env = os.getenv("X_UPLOAD_BEFORE_INSTAGRAM")
    if args.x_upload_before_instagram:
        x_upload_before_instagram = True
    elif x_order_env is not None:
        x_upload_before_instagram = _parse_bool(x_order_env, default=False)
    elif "X_UPLOAD_BEFORE_INSTAGRAM" in x_local_env:
        x_upload_before_instagram = _parse_bool(
            x_local_env.get("X_UPLOAD_BEFORE_INSTAGRAM"),
            default=bool(getattr(config, "X_UPLOAD_BEFORE_INSTAGRAM", False)),
        )
    else:
        # Auto-choose pre-IG order when X is allowed independently of IG success.
        x_upload_before_instagram = bool(
            getattr(config, "X_UPLOAD_BEFORE_INSTAGRAM", x_upload_on_ig_failure)
        )

    x_use_non_ig_variant = _parse_bool(
        os.getenv("X_USE_NON_IG_VARIANT", x_local_env.get("X_USE_NON_IG_VARIANT")),
        default=bool(getattr(config, "X_USE_NON_IG_VARIANT", True)),
    )
    x_retry_count = _coerce_int(
        os.getenv("X_RETRY_COUNT")
        or x_local_env.get("X_RETRY_COUNT")
        or getattr(config, "X_RETRY_COUNT", 3),
        3,
    )
    x_timeout_seconds = _coerce_int(
        os.getenv("X_TIMEOUT_SECONDS")
        or x_local_env.get("X_TIMEOUT_SECONDS")
        or getattr(config, "X_TIMEOUT_SECONDS", 120),
        120,
    )
    x_uploader = str(
        args.x_uploader
        or os.getenv("X_UPLOADER")
        or x_local_env.get("X_UPLOADER")
        or getattr(config, "X_UPLOADER", "api")
        or "api"
    ).strip().lower()
    if x_uploader not in {"api", "safe"}:
        x_uploader = "api"
    x_cookies_path = Path(
        os.getenv("X_COOKIES_FILE")
        or x_local_env.get("X_COOKIES_FILE")
        or str(args.x_cookies_file)
    )
    x_headless = bool(
        args.x_headless
        or _parse_bool(
            os.getenv("X_HEADLESS", x_local_env.get("X_HEADLESS")),
            default=bool(getattr(config, "X_HEADLESS", False)),
        )
    )
    x_safe_post_ready_timeout = _coerce_int(
        os.getenv("X_SAFE_POST_READY_TIMEOUT_SECONDS")
        or x_local_env.get("X_SAFE_POST_READY_TIMEOUT_SECONDS")
        or getattr(config, "X_SAFE_POST_READY_TIMEOUT_SECONDS", 60),
        60,
    )
    if x_safe_post_ready_timeout < 20:
        x_safe_post_ready_timeout = 20
    x_safe_post_click_attempts = _coerce_int(
        os.getenv("X_SAFE_POST_CLICK_ATTEMPTS")
        or x_local_env.get("X_SAFE_POST_CLICK_ATTEMPTS")
        or getattr(config, "X_SAFE_POST_CLICK_ATTEMPTS", 4),
        4,
    )
    if x_safe_post_click_attempts < 1:
        x_safe_post_click_attempts = 1

    if args.x_save_cookies:
        if SafeXUploader is None:
            raise SystemExit("safe_x_uploader is unavailable. Ensure selenium is installed.")
        x_cookie_helper = SafeXUploader(
            cookies_file=str(x_cookies_path),
            headless=x_headless,
            post_ready_timeout_seconds=x_safe_post_ready_timeout,
            post_click_attempts=x_safe_post_click_attempts,
        )
        ok = x_cookie_helper.save_cookies()
        raise SystemExit(0 if ok else 1)

    if x_upload_enabled and x_uploader == "api" and upload_x is None:
        print("[WARN] X upload enabled, but shared.x_uploader is unavailable.")
        x_upload_enabled = False
    if x_upload_enabled and x_uploader == "safe" and SafeXUploader is None:
        print("[WARN] X safe upload enabled, but safe_x_uploader is unavailable.")
        x_upload_enabled = False

    if x_upload_enabled:
        if x_uploader == "api":
            missing_fields = []
            if not x_consumer_key:
                missing_fields.append("X_CONSUMER_KEY")
            if not x_consumer_secret:
                missing_fields.append("X_CONSUMER_SECRET")
            if not x_access_token:
                missing_fields.append("X_ACCESS_TOKEN")
            if not x_access_token_secret:
                missing_fields.append("X_ACCESS_TOKEN_SECRET")
            if missing_fields:
                print(
                    "[WARN] X upload enabled but missing required settings: "
                    + ", ".join(missing_fields)
                    + f". Provide via args, env, or {x_secrets_path}."
                )
                x_upload_enabled = False
        else:
            if not x_cookies_path.exists():
                print(
                    f"[WARN] X safe upload enabled but cookie file is missing: {x_cookies_path}. "
                    "Run with --x-save-cookies first."
                )
                x_upload_enabled = False

    if x_upload_enabled:
        if x_upload_on_ig_failure:
            print("[INFO] X upload enabled (will upload even if IG confirmation is missing).")
        else:
            print("[INFO] X upload enabled (requires IG success).")
        if x_uploader == "safe":
            print(
                f"[INFO] X settings: uploader=safe, cookies={x_cookies_path}, "
                f"headless={x_headless}, use_non_ig_variant={x_use_non_ig_variant}, "
                f"order={'before_ig' if x_upload_before_instagram else 'after_ig'}, "
                f"post_ready_timeout={x_safe_post_ready_timeout}s, "
                f"post_click_attempts={x_safe_post_click_attempts}"
            )
        else:
            print(
                f"[INFO] X settings: uploader=api, use_non_ig_variant={x_use_non_ig_variant}, "
                f"retry_count={x_retry_count}, timeout={x_timeout_seconds}s, "
                f"order={'before_ig' if x_upload_before_instagram else 'after_ig'}"
            )

    lemon8_secrets_path = Path(args.lemon8_secrets_file)
    lemon8_local_env = load_env_values(lemon8_secrets_path)
    lemon8_enable_env = os.getenv("LEMON8_ENABLE")
    if lemon8_enable_env is not None:
        lemon8_feature_enabled = _parse_bool(lemon8_enable_env, default=True)
    elif "LEMON8_ENABLE" in lemon8_local_env:
        lemon8_feature_enabled = _parse_bool(
            lemon8_local_env.get("LEMON8_ENABLE"),
            default=bool(getattr(config, "LEMON8_ENABLE", True)),
        )
    else:
        lemon8_feature_enabled = bool(getattr(config, "LEMON8_ENABLE", True))

    lemon8_auto_env = os.getenv("LEMON8_AUTO_UPLOAD")
    if lemon8_auto_env is not None:
        lemon8_auto_upload = _parse_bool(lemon8_auto_env, default=False)
    elif "LEMON8_AUTO_UPLOAD" in lemon8_local_env:
        lemon8_auto_upload = _parse_bool(
            lemon8_local_env.get("LEMON8_AUTO_UPLOAD"),
            default=bool(getattr(config, "LEMON8_AUTO_UPLOAD", False)),
        )
    else:
        lemon8_auto_upload = bool(getattr(config, "LEMON8_AUTO_UPLOAD", False))

    lemon8_upload_enabled = bool(lemon8_feature_enabled and (args.enable_lemon8_upload or lemon8_auto_upload))
    if args.skip_lemon8:
        lemon8_upload_enabled = False

    lemon8_on_fail_env = os.getenv("LEMON8_UPLOAD_ON_IG_FAILURE")
    if args.lemon8_upload_on_ig_failure:
        lemon8_upload_on_ig_failure = True
    elif lemon8_on_fail_env is not None:
        lemon8_upload_on_ig_failure = _parse_bool(lemon8_on_fail_env, default=False)
    elif "LEMON8_UPLOAD_ON_IG_FAILURE" in lemon8_local_env:
        lemon8_upload_on_ig_failure = _parse_bool(
            lemon8_local_env.get("LEMON8_UPLOAD_ON_IG_FAILURE"),
            default=bool(getattr(config, "LEMON8_UPLOAD_ON_IG_FAILURE", False)),
        )
    else:
        lemon8_upload_on_ig_failure = bool(getattr(config, "LEMON8_UPLOAD_ON_IG_FAILURE", False))

    lemon8_uploader = str(
        args.lemon8_uploader
        or os.getenv("LEMON8_UPLOADER")
        or lemon8_local_env.get("LEMON8_UPLOADER")
        or getattr(config, "LEMON8_UPLOADER", "safe")
        or "safe"
    ).strip().lower()
    if lemon8_uploader not in {"safe"}:
        lemon8_uploader = "safe"
    lemon8_cookies_path = Path(
        os.getenv("LEMON8_COOKIES_FILE")
        or lemon8_local_env.get("LEMON8_COOKIES_FILE")
        or str(args.lemon8_cookies_file)
    )
    lemon8_headless = bool(
        args.lemon8_headless
        or _parse_bool(
            os.getenv("LEMON8_HEADLESS", lemon8_local_env.get("LEMON8_HEADLESS")),
            default=bool(getattr(config, "LEMON8_HEADLESS", False)),
        )
    )
    lemon8_use_non_ig_variant = _parse_bool(
        os.getenv("LEMON8_USE_NON_IG_VARIANT", lemon8_local_env.get("LEMON8_USE_NON_IG_VARIANT")),
        default=bool(getattr(config, "LEMON8_USE_NON_IG_VARIANT", True)),
    )

    if args.lemon8_save_cookies:
        if SafeLemon8Uploader is None:
            raise SystemExit("safe_lemon8_uploader is unavailable. Ensure selenium is installed.")
        lemon8_cookie_helper = SafeLemon8Uploader(
            cookies_file=str(lemon8_cookies_path),
            headless=lemon8_headless,
        )
        ok = lemon8_cookie_helper.save_cookies()
        raise SystemExit(0 if ok else 1)

    if lemon8_upload_enabled and SafeLemon8Uploader is None:
        print("[WARN] Lemon8 upload enabled, but safe_lemon8_uploader is unavailable.")
        lemon8_upload_enabled = False

    if lemon8_upload_enabled and not lemon8_cookies_path.exists():
        print(
            f"[WARN] Lemon8 upload enabled but cookie file is missing: {lemon8_cookies_path}. "
            "Run with --lemon8-save-cookies first."
        )
        lemon8_upload_enabled = False

    if lemon8_upload_enabled:
        if lemon8_upload_on_ig_failure:
            print("[INFO] Lemon8 upload enabled (will upload even if IG confirmation is missing).")
        else:
            print("[INFO] Lemon8 upload enabled (requires IG success).")
        print(
            f"[INFO] Lemon8 settings: uploader={lemon8_uploader}, cookies={lemon8_cookies_path}, "
            f"headless={lemon8_headless}, use_non_ig_variant={lemon8_use_non_ig_variant}"
        )

    rednote_secrets_path = Path(args.rednote_secrets_file)
    rednote_local_env = load_env_values(rednote_secrets_path)
    rednote_enable_env = os.getenv("REDNOTE_ENABLE")
    if rednote_enable_env is not None:
        rednote_feature_enabled = _parse_bool(rednote_enable_env, default=True)
    elif "REDNOTE_ENABLE" in rednote_local_env:
        rednote_feature_enabled = _parse_bool(
            rednote_local_env.get("REDNOTE_ENABLE"),
            default=bool(getattr(config, "REDNOTE_ENABLE", True)),
        )
    else:
        rednote_feature_enabled = bool(getattr(config, "REDNOTE_ENABLE", True))

    rednote_auto_env = os.getenv("REDNOTE_AUTO_UPLOAD")
    if rednote_auto_env is not None:
        rednote_auto_upload = _parse_bool(rednote_auto_env, default=False)
    elif "REDNOTE_AUTO_UPLOAD" in rednote_local_env:
        rednote_auto_upload = _parse_bool(
            rednote_local_env.get("REDNOTE_AUTO_UPLOAD"),
            default=bool(getattr(config, "REDNOTE_AUTO_UPLOAD", False)),
        )
    else:
        rednote_auto_upload = bool(getattr(config, "REDNOTE_AUTO_UPLOAD", False))

    rednote_upload_enabled = bool(
        rednote_feature_enabled and (args.enable_rednote_upload or rednote_auto_upload)
    )
    if args.skip_rednote:
        rednote_upload_enabled = False

    rednote_on_fail_env = os.getenv("REDNOTE_UPLOAD_ON_IG_FAILURE")
    if args.rednote_upload_on_ig_failure:
        rednote_upload_on_ig_failure = True
    elif rednote_on_fail_env is not None:
        rednote_upload_on_ig_failure = _parse_bool(rednote_on_fail_env, default=False)
    elif "REDNOTE_UPLOAD_ON_IG_FAILURE" in rednote_local_env:
        rednote_upload_on_ig_failure = _parse_bool(
            rednote_local_env.get("REDNOTE_UPLOAD_ON_IG_FAILURE"),
            default=bool(getattr(config, "REDNOTE_UPLOAD_ON_IG_FAILURE", False)),
        )
    else:
        rednote_upload_on_ig_failure = bool(getattr(config, "REDNOTE_UPLOAD_ON_IG_FAILURE", False))

    rednote_uploader = str(
        args.rednote_uploader
        or os.getenv("REDNOTE_UPLOADER")
        or rednote_local_env.get("REDNOTE_UPLOADER")
        or getattr(config, "REDNOTE_UPLOADER", "safe")
        or "safe"
    ).strip().lower()
    if rednote_uploader not in {"safe"}:
        rednote_uploader = "safe"
    rednote_cookies_path = Path(
        os.getenv("REDNOTE_COOKIES_FILE")
        or rednote_local_env.get("REDNOTE_COOKIES_FILE")
        or str(args.rednote_cookies_file)
    )
    rednote_headless = bool(
        args.rednote_headless
        or _parse_bool(
            os.getenv("REDNOTE_HEADLESS", rednote_local_env.get("REDNOTE_HEADLESS")),
            default=bool(getattr(config, "REDNOTE_HEADLESS", False)),
        )
    )
    rednote_use_non_ig_variant = _parse_bool(
        os.getenv("REDNOTE_USE_NON_IG_VARIANT", rednote_local_env.get("REDNOTE_USE_NON_IG_VARIANT")),
        default=bool(getattr(config, "REDNOTE_USE_NON_IG_VARIANT", True)),
    )

    if args.rednote_save_cookies:
        if SafeRednoteUploader is None:
            raise SystemExit("safe_rednote_uploader is unavailable. Ensure selenium is installed.")
        rednote_cookie_helper = SafeRednoteUploader(
            cookies_file=str(rednote_cookies_path),
            headless=rednote_headless,
        )
        ok = rednote_cookie_helper.save_cookies()
        raise SystemExit(0 if ok else 1)

    if rednote_upload_enabled and SafeRednoteUploader is None:
        print("[WARN] Rednote upload enabled, but safe_rednote_uploader is unavailable.")
        rednote_upload_enabled = False

    if rednote_upload_enabled and not rednote_cookies_path.exists():
        print(
            f"[WARN] Rednote upload enabled but cookie file is missing: {rednote_cookies_path}. "
            "Run with --rednote-save-cookies first."
        )
        rednote_upload_enabled = False

    if rednote_upload_enabled:
        if rednote_upload_on_ig_failure:
            print("[INFO] Rednote upload enabled (will upload even if IG confirmation is missing).")
        else:
            print("[INFO] Rednote upload enabled (requires IG success).")
        print(
            f"[INFO] Rednote settings: uploader={rednote_uploader}, cookies={rednote_cookies_path}, "
            f"headless={rednote_headless}, use_non_ig_variant={rednote_use_non_ig_variant}"
        )

    # Build expected videos from run context (or ALL_GAME_MODES)
    video_paths = [
        build_platform_video_path(gm, day_number=run_day_number, platform_target=run_platform_target)
        for gm in run_game_modes
    ]
    if args.max_videos and args.max_videos > 0:
        original_count = len(video_paths)
        video_paths = video_paths[: args.max_videos]
        print(f"[INFO] Limiting videos: {len(video_paths)}/{original_count} (--max-videos {args.max_videos})")

    if args.skip_stats:
        print("[WARN] Skipping stats/history push (--skip-stats).")
    else:
        print("[INFO] Pushing stats/history to GitHub...")
        push_stats(args.push_message)

    if not args.enable_uploads:
        if args.skip_stats:
            print("[OK] Done (stats skipped, video upload disabled).")
        else:
            print("[OK] Done (stats pushed only - video upload disabled).")
        return

    if args.pre_upload_wait_seconds > 0:
        print(
            "[WAIT] Waiting "
            f"{args.pre_upload_wait_seconds / 60:.1f} minutes after publish before uploads..."
        )
        time.sleep(args.pre_upload_wait_seconds)

    session_path = os.getenv("IG_SESSION_FILE", str(args.session_file))
    if not session_path:
        raise SystemExit("Missing session file. Provide --session-file or set IG_SESSION_FILE.")
    session_path = Path(session_path)
    ig_cookies_path = Path(os.getenv("IG_COOKIES_FILE", str(args.ig_cookies_file)))
    tiktok_session_path = os.getenv("TIKTOK_SESSION_FILE", str(args.tiktok_session_file))

    ig_safe = None
    ig_export = None
    snap_safe = None
    x_safe = None
    lemon8_safe = None
    rednote_safe = None

    def start_export_session(existing_driver=None):
        from persistent_instagram_uploader import PersistentInstagramUploader
        export_download_dir = getattr(config, "IG_EXPORT_DOWNLOAD_DIR", "")
        exporter = PersistentInstagramUploader(
            cookies_file=str(ig_cookies_path),
            headless=args.ig_headless,
            download_dir=export_download_dir or None,
        )
        if existing_driver is not None:
            exporter.attach_existing_driver(existing_driver)
            return exporter
        if not exporter.start_session():
            raise SystemExit("Failed to start persistent Instagram session for export.")
        return exporter

    client = None
    if args.ig_uploader == "instagrapi" and not args.skip_instagram:
        if args.wait_for_login:
            ig_profile_url = args.ig_profile_url
            if not ig_profile_url:
                ig_username = getattr(config, "INSTAGRAM_USERNAME", "")
                if ig_username:
                    ig_profile_url = f"https://www.instagram.com/{ig_username}/"
                else:
                    ig_profile_url = "https://www.instagram.com/accounts/login/"
            wait_for_manual_login(ig_profile_url)
        client = load_client(session_path)
    tiktok_session_id = None
    if tiktok_session_path:
        try:
            tiktok_session_id = load_tiktok_session(Path(tiktok_session_path))
        except Exception as e:
            print(f"[WARN] TikTok session load failed: {e}. TikTok uploads will be skipped.")

    if snap_upload_enabled and snap_uploader == "safe":
        snap_safe = SafeSnapchatUploader(
            cookies_file=str(snap_cookies_path),
            headless=snap_headless,
            spotlight_only=snap_safe_spotlight_only,
            profile_dir=snap_profile_dir,
        )
        if not snap_safe.start_session():
            print("[WARN] Failed to start Snapchat safe session. Snapchat uploads will be skipped.")
            snap_upload_enabled = False

    if x_upload_enabled and x_uploader == "safe":
        x_safe = SafeXUploader(
            cookies_file=str(x_cookies_path),
            headless=x_headless,
            post_ready_timeout_seconds=x_safe_post_ready_timeout,
            post_click_attempts=x_safe_post_click_attempts,
        )
        if not x_safe.start_session():
            print("[WARN] Failed to start safe X session. X uploads will be skipped.")
            x_upload_enabled = False

    if lemon8_upload_enabled and lemon8_uploader == "safe":
        lemon8_safe = SafeLemon8Uploader(
            cookies_file=str(lemon8_cookies_path),
            headless=lemon8_headless,
        )
        if not lemon8_safe.start_session():
            print("[WARN] Failed to start Lemon8 safe session. Lemon8 uploads will be skipped.")
            lemon8_upload_enabled = False

    if rednote_upload_enabled and rednote_uploader == "safe":
        rednote_safe = SafeRednoteUploader(
            cookies_file=str(rednote_cookies_path),
            headless=rednote_headless,
        )
        if not rednote_safe.start_session():
            print("[WARN] Failed to start Rednote safe session. Rednote uploads will be skipped.")
            rednote_upload_enabled = False

    if args.ig_export_followers and not args.ig_export_after_uploads:
        if args.ig_uploader == "safe":
            ig_export = start_export_session()
            ok = run_ig_export(ig_export, args)
            if not ok:
                print("IG export failed; continuing with uploads.")
            ig_export.close_session()
            ig_export = None
        else:
            run_ig_export(None, args)

    print("[INFO] Uploading videos as Reels/TikTok/YouTube/Snapchat/X/Lemon8/Rednote...")
    try:
        if args.ig_uploader == "safe" and not args.skip_instagram:
            from safe_instagram_uploader import SafeInstagramUploader
            ig_safe = SafeInstagramUploader(
                cookies_file=str(ig_cookies_path),
                headless=args.ig_headless,
            )
            if not ig_safe.start_session():
                raise SystemExit("Failed to start safe Instagram session.")

        snapchat_uploaded_keys: set[str] = set()
        x_uploaded_keys: set[str] = set()
        lemon8_uploaded_keys: set[str] = set()
        rednote_uploaded_keys: set[str] = set()

        def _attempt_x_upload_for_video(
            *,
            base_video_path: Path,
            game_mode: str,
            actual_day_number: int,
            day_value: int,
            base_caption: str,
            pre_ig_mode: bool = False,
        ) -> bool:
            """Attempt one X upload for a video and return True when attempt was made."""
            if not x_upload_enabled:
                return False

            if x_use_non_ig_variant:
                x_video_path = resolve_platform_video_path(
                    base_video_path=base_video_path,
                    platform="x",
                    game_mode=game_mode,
                    day_number=actual_day_number,
                )
            else:
                x_video_path = base_video_path

            if x_video_path is None:
                print(f"[WARN] X: Skipping {base_video_path.name} because non-IG variant is unavailable.")
                return True

            dedupe_key = f"{actual_day_number}:{game_mode}:{x_video_path.name}"
            if dedupe_key in x_uploaded_keys:
                print(f"[INFO] X: Skipping duplicate upload key {dedupe_key}")
                return True

            if pre_ig_mode:
                print(f"[INFO] X: Pre-IG upload for {x_video_path.name}")
            else:
                print(f"[INFO] X: Uploading {x_video_path.name}")

            if x_uploader == "safe":
                x_text = build_x_post_text(
                    caption=base_caption,
                    game_mode=game_mode,
                    day_number=day_value,
                )
                safe_ok = bool(
                    x_safe and x_safe.upload_post(
                        video_path=x_video_path,
                        text=x_text,
                        reuse_session=True,
                    )
                )
                if safe_ok:
                    print("[OK] X posted via safe uploader.")
                else:
                    print(f"[WARN] X safe upload failed for {x_video_path.name}")
            else:
                x_result = upload_x(
                    video_path=x_video_path,
                    caption=base_caption,
                    game_mode=game_mode,
                    day_number=day_value,
                    consumer_key=x_consumer_key,
                    consumer_secret=x_consumer_secret,
                    access_token=x_access_token,
                    access_token_secret=x_access_token_secret,
                    upload_api=x_upload_api_url,
                    api_base=x_api_base,
                    retry_count=x_retry_count,
                    timeout_seconds=x_timeout_seconds,
                    logger=print,
                )
                if x_result.get("ok"):
                    print(
                        f"[OK] X posted: media_id={x_result.get('media_id')}, "
                        f"tweet_id={x_result.get('tweet_id') or '-'}"
                    )
                else:
                    errors = x_result.get("errors") or []
                    print(f"[WARN] X upload failed for {x_video_path.name}: {errors}")

            x_uploaded_keys.add(dedupe_key)
            return True

        for idx, video_path in enumerate(video_paths):
            game_mode = video_path.stem.split("_day_")[0] if "_day_" in video_path.stem else video_path.stem
            record_game_type = resolve_record_game_type(game_mode, run_platform_target)
            actual_day_number = int(run_day_number)
            min_video_mtime = run_context_min_epoch if args.queue_ready_videos else None
            fresh_video_ready = False
            try:
                fresh_video_ready = video_path.exists() and (
                    min_video_mtime is None or video_path.stat().st_mtime >= min_video_mtime
                )
            except Exception:
                fresh_video_ready = False

            if not fresh_video_ready:
                if args.wait_for_videos:
                    if args.queue_ready_videos and min_video_mtime is not None:
                        print(
                            f"[WAIT] Waiting for fresh video for {game_mode} Day {actual_day_number}: {video_path}"
                        )
                    else:
                        print(f"[WAIT] Missing video: {video_path}. Waiting up to {args.wait_max_seconds}s...")
                    found = wait_for_video(
                        video_path,
                        args.wait_max_seconds,
                        args.wait_poll_seconds,
                        min_mtime=min_video_mtime,
                    )
                    if not found:
                        print(f"[WARN] Timed out waiting for video: {video_path}")
                        continue
                    print(f"[OK] Found video after wait: {video_path}")
                else:
                    print(f"[WARN] Skipping missing video: {video_path}")
                    continue

            ready_game_payload = None
            if args.queue_ready_videos:
                print(f"[WAIT] Waiting for game data: {game_mode} Day {actual_day_number}")
                ready_game_payload = wait_for_game_payload(
                    actual_day_number,
                    record_game_type,
                    max_seconds=args.wait_max_seconds,
                    poll_seconds=args.wait_poll_seconds,
                    min_timestamp=run_context_timestamp,
                    prefer_events=True,
                    events_scan_max_files=args.events_scan_max_files,
                )
                if ready_game_payload is None:
                    print(f"[WARN] Timed out waiting for game data: {game_mode} Day {actual_day_number}")
                    continue
                print(
                    "[OK] Game data ready: "
                    f"{ready_game_payload.get('game_id')} ({ready_game_payload.get('timestamp')})"
                )
                if args.ready_grace_seconds > 0:
                    print(
                        f"[WAIT] Waiting {args.ready_grace_seconds / 60:.1f} minutes "
                        f"for webhook/event propagation before uploading {video_path.name}..."
                    )
                    time.sleep(args.ready_grace_seconds)

            day_value = _display_day_for_mode(game_mode, actual_day_number)
            base_caption = args.caption_template.format(game_mode=game_mode, day_number=day_value)
            skip_top10_modes = set(getattr(config, "TOP10_SKIP_GAME_MODES", []))
            if _is_mode_in_skip_list(game_mode, skip_top10_modes):
                ig_caption = base_caption
            else:
                if ready_game_payload is not None:
                    top_users = _extract_top_usernames_from_payload(ready_game_payload, limit=10)
                else:
                    top_users = get_top_usernames_for_game(actual_day_number, record_game_type, limit=10)
                ig_caption = base_caption + format_top_users_block(top_users)

            x_attempted_pre_ig = False
            if x_upload_enabled and x_upload_before_instagram:
                if x_upload_on_ig_failure or args.skip_instagram:
                    x_attempted_pre_ig = _attempt_x_upload_for_video(
                        base_video_path=video_path,
                        game_mode=game_mode,
                        actual_day_number=actual_day_number,
                        day_value=day_value,
                        base_caption=base_caption,
                        pre_ig_mode=True,
                    )
                else:
                    print(
                        f"[INFO] X: Pre-IG order requested but IG-success gating is active for {video_path.name}; "
                        "deferring X upload until IG result is known."
                    )

            ig_ok = False
            if args.skip_instagram:
                print(f"[INFO] IG: Skipping {video_path.name} (--skip-instagram)")
            else:
                # Instagram upload
                print(f"[INFO] IG: Uploading {video_path.name}")
                if args.ig_uploader == "safe":
                    ig_ok = bool(
                        ig_safe.upload_reel(
                            str(video_path),
                            ig_caption,
                            reuse_session=True,
                            game_mode=game_mode,
                        )
                    )
                else:
                    ig_ok = upload_instagram(client, video_path, ig_caption)

            if fb_upload_enabled and (ig_ok or fb_upload_on_ig_failure):
                if not ig_ok and fb_upload_on_ig_failure:
                    print(
                        f"[WARN] IG upload not confirmed for {video_path.name}; "
                        "attempting FB upload anyway (FACEBOOK_UPLOAD_ON_IG_FAILURE)."
                    )
                fb_video_path = resolve_platform_video_path(
                    base_video_path=video_path,
                    platform="facebook",
                    game_mode=game_mode,
                    day_number=actual_day_number,
                )
                if fb_video_path is None:
                    print(f"[WARN] FB: Skipping {video_path.name} because non-IG variant is unavailable.")
                else:
                    print(f"[INFO] FB: Uploading {fb_video_path.name} to Page {fb_page_id}")
                    upload_facebook_page_video(
                        video_path=fb_video_path,
                        caption=ig_caption,
                        page_id=fb_page_id,
                        access_token=fb_access_token,
                        api_version=fb_api_version,
                        game_mode=game_mode,
                        day_number=actual_day_number,
                    )

            # TikTok upload
            if tiktok_session_id:
                tiktok_video_path = resolve_platform_video_path(
                    base_video_path=video_path,
                    platform="tiktok",
                    game_mode=game_mode,
                    day_number=actual_day_number,
                )
                if tiktok_video_path is None:
                    print(f"[WARN] TikTok: Skipping {video_path.name} because non-IG variant is unavailable.")
                else:
                    print(f"[INFO] TikTok: Uploading {tiktok_video_path.name}")
                    upload_tiktok(tiktok_session_id, tiktok_video_path, base_caption)

            # YouTube upload
            skip_youtube_modes = set(getattr(config, "YOUTUBE_SKIP_GAME_MODES", []))
            if not args.skip_youtube and not _is_mode_in_skip_list(game_mode, skip_youtube_modes):
                youtube_video_path = resolve_platform_video_path(
                    base_video_path=video_path,
                    platform="youtube",
                    game_mode=game_mode,
                    day_number=actual_day_number,
                )
                if youtube_video_path is None:
                    print(f"[WARN] YouTube: Skipping {video_path.name} because non-IG variant is unavailable.")
                else:
                    print(f"[INFO] YouTube: Uploading {youtube_video_path.name}")
                    upload_youtube(
                        video_path=youtube_video_path,
                        game_mode=game_mode,
                        day_number=day_value,
                        schedule_hours=args.youtube_schedule_hours,
                        privacy=args.youtube_privacy,
                        platform_target=run_platform_target,
                        record_game_type=record_game_type,
                    )
            elif game_mode in skip_youtube_modes:
                print(f"Skipping YouTube upload for {game_mode} (config.YOUTUBE_SKIP_GAME_MODES).")

            # Snapchat upload
            if snap_upload_enabled and (ig_ok or snap_upload_on_ig_failure):
                if not ig_ok and snap_upload_on_ig_failure:
                    print(
                        f"[WARN] IG upload not confirmed for {video_path.name}; "
                        "attempting Snapchat upload anyway (SNAPCHAT_UPLOAD_ON_IG_FAILURE)."
                    )

                if snap_use_non_ig_variant:
                    snapchat_video_path = resolve_platform_video_path(
                        base_video_path=video_path,
                        platform="snapchat",
                        game_mode=game_mode,
                        day_number=actual_day_number,
                    )
                else:
                    snapchat_video_path = video_path

                if snapchat_video_path is None:
                    print(f"[WARN] Snapchat: Skipping {video_path.name} because non-IG variant is unavailable.")
                else:
                    dedupe_key = f"{actual_day_number}:{game_mode}:{snapchat_video_path.name}"
                    if dedupe_key in snapchat_uploaded_keys:
                        print(f"[INFO] Snapchat: Skipping duplicate upload key {dedupe_key}")
                    else:
                        print(f"[INFO] Snapchat: Uploading {snapchat_video_path.name}")
                        if snap_uploader == "safe":
                            snap_text = build_snapchat_post_text(
                                caption=base_caption,
                                game_mode=game_mode,
                                day_number=day_value,
                            )
                            safe_ok = bool(
                                snap_safe and snap_safe.upload_post(
                                    video_path=snapchat_video_path,
                                    text=snap_text,
                                    reuse_session=True,
                                    spotlight_only=snap_safe_spotlight_only,
                                )
                            )
                            if safe_ok:
                                print("[OK] Snapchat posted via safe uploader (Spotlight).")
                            else:
                                print(f"[WARN] Snapchat safe upload failed for {snapchat_video_path.name}")
                        else:
                            snap_result = upload_snapchat(
                                video_path=snapchat_video_path,
                                game_mode=game_mode,
                                day_number=day_value,
                                caption=base_caption,
                                profile_id=snap_profile_id,
                                client_id=snap_client_id,
                                client_secret=snap_client_secret,
                                redirect_uri=snap_redirect_uri,
                                access_token_path=snap_access_token_path,
                                refresh_token_path=snap_refresh_token_path,
                                scope=snap_scope,
                                api_base=snap_api_base,
                                enable_story_post=snap_story_enabled,
                                enable_spotlight_post=snap_spotlight_enabled,
                                spotlight_locale=snap_spotlight_locale,
                                spotlight_skip_save_to_profile=snap_spotlight_skip_save,
                                retry_count=snap_retry_count,
                                timeout_seconds=snap_timeout_seconds,
                                logger=print,
                            )
                            if snap_result.get("ok"):
                                story_id = str(((snap_result.get("story") or {}).get("id") or "")).strip()
                                spotlight_id = str(((snap_result.get("spotlight") or {}).get("id") or "")).strip()
                                print(
                                    f"[OK] Snapchat posted: media_id={snap_result.get('media_id')}, "
                                    f"story_id={story_id or '-'}, spotlight_id={spotlight_id or '-'}"
                                )
                            else:
                                errors = snap_result.get("errors") or []
                                print(f"[WARN] Snapchat upload failed for {snapchat_video_path.name}: {errors}")
                        snapchat_uploaded_keys.add(dedupe_key)

            # X upload
            if x_upload_enabled and not x_attempted_pre_ig and (ig_ok or x_upload_on_ig_failure):
                if not ig_ok and x_upload_on_ig_failure:
                    print(
                        f"[WARN] IG upload not confirmed for {video_path.name}; "
                        "attempting X upload anyway (X_UPLOAD_ON_IG_FAILURE)."
                    )
                _attempt_x_upload_for_video(
                    base_video_path=video_path,
                    game_mode=game_mode,
                    actual_day_number=actual_day_number,
                    day_value=day_value,
                    base_caption=base_caption,
                    pre_ig_mode=False,
                )

            # Lemon8 upload
            if lemon8_upload_enabled and (ig_ok or lemon8_upload_on_ig_failure):
                if not ig_ok and lemon8_upload_on_ig_failure:
                    print(
                        f"[WARN] IG upload not confirmed for {video_path.name}; "
                        "attempting Lemon8 upload anyway (LEMON8_UPLOAD_ON_IG_FAILURE)."
                    )

                if lemon8_use_non_ig_variant:
                    lemon8_video_path = resolve_platform_video_path(
                        base_video_path=video_path,
                        platform="lemon8",
                        game_mode=game_mode,
                        day_number=actual_day_number,
                    )
                else:
                    lemon8_video_path = video_path

                if lemon8_video_path is None:
                    print(f"[WARN] Lemon8: Skipping {video_path.name} because non-IG variant is unavailable.")
                else:
                    dedupe_key = f"{actual_day_number}:{game_mode}:{lemon8_video_path.name}"
                    if dedupe_key in lemon8_uploaded_keys:
                        print(f"[INFO] Lemon8: Skipping duplicate upload key {dedupe_key}")
                    else:
                        print(f"[INFO] Lemon8: Uploading {lemon8_video_path.name}")
                        lemon8_text = build_lemon8_post_text(
                            caption=base_caption,
                            game_mode=game_mode,
                            day_number=day_value,
                        )
                        lemon8_ok = bool(
                            lemon8_safe and lemon8_safe.upload_post(
                                video_path=lemon8_video_path,
                                text=lemon8_text,
                                reuse_session=True,
                            )
                        )
                        if lemon8_ok:
                            print("[OK] Lemon8 posted via safe uploader.")
                        else:
                            print(f"[WARN] Lemon8 upload failed for {lemon8_video_path.name}")
                        lemon8_uploaded_keys.add(dedupe_key)

            # Rednote upload
            if rednote_upload_enabled and (ig_ok or rednote_upload_on_ig_failure):
                if not ig_ok and rednote_upload_on_ig_failure:
                    print(
                        f"[WARN] IG upload not confirmed for {video_path.name}; "
                        "attempting Rednote upload anyway (REDNOTE_UPLOAD_ON_IG_FAILURE)."
                    )

                if rednote_use_non_ig_variant:
                    rednote_video_path = resolve_platform_video_path(
                        base_video_path=video_path,
                        platform="rednote",
                        game_mode=game_mode,
                        day_number=actual_day_number,
                    )
                else:
                    rednote_video_path = video_path

                if rednote_video_path is None:
                    print(f"[WARN] Rednote: Skipping {video_path.name} because non-IG variant is unavailable.")
                else:
                    dedupe_key = f"{actual_day_number}:{game_mode}:{rednote_video_path.name}"
                    if dedupe_key in rednote_uploaded_keys:
                        print(f"[INFO] Rednote: Skipping duplicate upload key {dedupe_key}")
                    else:
                        print(f"[INFO] Rednote: Uploading {rednote_video_path.name}")
                        rednote_text = build_rednote_post_text(
                            caption=base_caption,
                            game_mode=game_mode,
                            day_number=day_value,
                        )
                        rednote_ok = bool(
                            rednote_safe and rednote_safe.upload_post(
                                video_path=rednote_video_path,
                                text=rednote_text,
                                reuse_session=True,
                            )
                        )
                        if rednote_ok:
                            print("[OK] Rednote posted via safe uploader.")
                        else:
                            print(f"[WARN] Rednote upload failed for {rednote_video_path.name}")
                        rednote_uploaded_keys.add(dedupe_key)

            # Delay before next upload (except after last one)
            if idx < len(video_paths) - 1:
                delay_seconds = None
                if args.upload_interval_minutes is not None:
                    delay_seconds = args.upload_interval_minutes * 60
                elif args.delay_seconds is not None and args.delay_seconds > 0:
                    variation = args.delay_seconds * 0.2
                    delay_seconds = args.delay_seconds + random.uniform(-variation, variation)
                elif args.delay_min_seconds and args.delay_max_seconds:
                    low = min(args.delay_min_seconds, args.delay_max_seconds)
                    high = max(args.delay_min_seconds, args.delay_max_seconds)
                    delay_seconds = random.uniform(low, high)

                if delay_seconds and delay_seconds > 0:
                    print(f"[WAIT] Waiting {delay_seconds/60:.1f} minutes before next upload...")
                    time.sleep(delay_seconds)

        if args.ig_export_followers and args.ig_export_after_uploads:
            if args.ig_uploader == "safe":
                existing_driver = ig_safe.driver if ig_safe and ig_safe.driver else None
                ig_export = start_export_session(existing_driver=existing_driver)
                ok = run_ig_export(ig_export, args)
                if not ok:
                    print("IG export failed after uploads.")
                ig_export.close_session()
                ig_export = None
            else:
                run_ig_export(None, args)

    finally:
        if ig_safe:
            ig_safe.close_session()
        if snap_safe:
            snap_safe.close_session()
        if x_safe:
            x_safe.close_session()
        if lemon8_safe:
            lemon8_safe.close_session()
        if rednote_safe:
            rednote_safe.close_session()
        if ig_export:
            ig_export.close_session()

    print("[OK] Done.")


if __name__ == "__main__":
    main()
