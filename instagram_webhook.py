# instagram_webhook.py
# Flask server to handle Instagram webhook events for automated DM responses.
#
# Setup:
# 1. pip install flask requests python-dotenv
# 2. Copy .env.example to .env and fill in your credentials
# 3. Run: python instagram_webhook.py
# 4. In another terminal: ngrok http 5000
# 5. Copy ngrok HTTPS URL to Meta webhook config
# 6. Use VERIFY_TOKEN below as the verify token in Meta

from flask import Flask, request, jsonify
import requests
import json
import os
import sys
import re
import time
import random
from datetime import datetime, timezone, timedelta
import threading
import queue
from collections import OrderedDict
from pathlib import Path
from dotenv import load_dotenv
import config
import importlib.util

upsert_facebook_join = None
lookup_username_by_facebook_id = None
remember_facebook_media_mapping = None
lookup_facebook_media_mapping = None
upsert_youtube_join = None
lookup_username_by_youtube_channel_id = None
remember_youtube_media_mapping = None
lookup_youtube_media_mapping = None

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# Ensure UTF-8 output for logs on Windows (prevents emoji crashes)
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
        except Exception:
            pass

# Load environment variables from .env file (always relative to this file)
BASE_DIR = Path(__file__).resolve().parent


def _load_module_from_path(module_name: str, module_path: Path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(module_path))
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


_fb_join_module = _load_module_from_path(
    "facebook_join_store_local",
    BASE_DIR / "shared" / "facebook_join_store.py",
)
if _fb_join_module is not None:
    upsert_facebook_join = getattr(_fb_join_module, "upsert_facebook_join", None)
    lookup_username_by_facebook_id = getattr(_fb_join_module, "lookup_username_by_facebook_id", None)
else:
    print("Warning: Could not load shared/facebook_join_store.py")

_fb_map_module = _load_module_from_path(
    "facebook_media_map_local",
    BASE_DIR / "shared" / "facebook_media_map.py",
)
if _fb_map_module is not None:
    remember_facebook_media_mapping = getattr(_fb_map_module, "remember_mapping", None)
    lookup_facebook_media_mapping = getattr(_fb_map_module, "lookup_mapping", None)
else:
    print("Warning: Could not load shared/facebook_media_map.py")

_yt_join_module = _load_module_from_path(
    "youtube_join_store_local",
    BASE_DIR / "shared" / "youtube_join_store.py",
)
if _yt_join_module is not None:
    upsert_youtube_join = getattr(_yt_join_module, "upsert_youtube_join", None)
    lookup_username_by_youtube_channel_id = getattr(
        _yt_join_module,
        "lookup_username_by_youtube_channel_id",
        None,
    )
else:
    print("Warning: Could not load shared/youtube_join_store.py")

_yt_map_module = _load_module_from_path(
    "youtube_media_map_local",
    BASE_DIR / "shared" / "youtube_media_map.py",
)
if _yt_map_module is not None:
    remember_youtube_media_mapping = getattr(_yt_map_module, "remember_mapping", None)
    lookup_youtube_media_mapping = getattr(_yt_map_module, "lookup_mapping", None)
else:
    print("Warning: Could not load shared/youtube_media_map.py")

load_dotenv(dotenv_path=BASE_DIR / ".env")

app = Flask(__name__)

# ============== CONFIGURATION ==============
# Choose any secret string - use this same value in Meta's webhook config
VERIFY_TOKEN = "FBG_WEBHOOK_SECRET_2026"

# Control debug/reloader (useful for headless/background runs)
WEBHOOK_DEBUG = os.getenv("WEBHOOK_DEBUG", "1").strip().lower() not in ("0", "false", "no")
WEBHOOK_USE_RELOADER = os.getenv("WEBHOOK_USE_RELOADER", "1").strip().lower() not in ("0", "false", "no")

# These are loaded from .env file (never commit real values!)
INSTAGRAM_ACCESS_TOKEN_APP = os.getenv("INSTAGRAM_ACCESS_TOKEN_APP", "YOUR_ACCESS_TOKEN_HERE")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "YOUR_ACCOUNT_ID_HERE")


def _parse_bool(value, default=False):
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


def _parse_keyword_list(value, default):
    if value is None:
        return [str(k).strip().lower() for k in (default or []) if str(k).strip()]
    if isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        text = str(value or "")
        if "," in text:
            items = [part.strip() for part in text.split(",")]
        else:
            items = [part.strip() for part in text.split()]
    normalized = [str(item).strip().lower() for item in items if str(item).strip()]
    if normalized:
        return normalized
    return [str(k).strip().lower() for k in (default or []) if str(k).strip()]


def _load_env_values(path: Path) -> dict:
    values = {}
    try:
        if not path.exists():
            return values
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key] = value
    except Exception as exc:
        print(f"Failed to load env values from {path}: {exc}")
    return values


FB_SECRETS_FILE = Path(
    str(getattr(config, "FACEBOOK_WEBHOOK_SECRETS_FILE", "facebook_page_publish.local.env") or "facebook_page_publish.local.env")
)
if not FB_SECRETS_FILE.is_absolute():
    FB_SECRETS_FILE = BASE_DIR / FB_SECRETS_FILE
_FB_ENV = _load_env_values(FB_SECRETS_FILE)

FACEBOOK_PAGE_ACCESS_TOKEN = (
    os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    or _FB_ENV.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    or getattr(config, "FACEBOOK_PAGE_ACCESS_TOKEN", "")
)
FACEBOOK_PAGE_ID = (
    os.getenv("FACEBOOK_PAGE_ID")
    or _FB_ENV.get("FACEBOOK_PAGE_ID")
    or getattr(config, "FACEBOOK_PAGE_ID", "")
)
FACEBOOK_GRAPH_API_VERSION = (
    os.getenv("FACEBOOK_GRAPH_API_VERSION")
    or _FB_ENV.get("FACEBOOK_GRAPH_API_VERSION")
    or getattr(config, "FACEBOOK_GRAPH_API_VERSION", "v18.0")
)
FACEBOOK_ENABLE_JOIN_CAPTURE = _parse_bool(
    os.getenv("FACEBOOK_ENABLE_JOIN_CAPTURE"),
    default=bool(getattr(config, "FACEBOOK_ENABLE_JOIN_CAPTURE", True)),
)
FACEBOOK_ENABLE_RESULT_REPLIES = _parse_bool(
    os.getenv("FACEBOOK_ENABLE_RESULT_REPLIES"),
    default=bool(getattr(config, "FACEBOOK_ENABLE_RESULT_REPLIES", False)),
)
FACEBOOK_JOIN_ACK_REPLY_ENABLED = _parse_bool(
    os.getenv("FACEBOOK_JOIN_ACK_REPLY_ENABLED"),
    default=bool(getattr(config, "FACEBOOK_JOIN_ACK_REPLY_ENABLED", True)),
)
FACEBOOK_JOIN_ACK_REPLY_TEXT = str(
    os.getenv("FACEBOOK_JOIN_ACK_REPLY_TEXT")
    or getattr(config, "FACEBOOK_JOIN_ACK_REPLY_TEXT", "You're in. You'll be added to future games.")
).strip()
FACEBOOK_JOIN_ALREADY_REPLY_TEXT = str(
    os.getenv("FACEBOOK_JOIN_ALREADY_REPLY_TEXT")
    or getattr(
        config,
        "FACEBOOK_JOIN_ALREADY_REPLY_TEXT",
        'You are already part of the games. Comment "RESULT" to see how you did.',
    )
).strip()
FACEBOOK_RESULT_FUTURE_GAMES_REPLY_TEXT = str(
    os.getenv("FACEBOOK_RESULT_FUTURE_GAMES_REPLY_TEXT")
    or getattr(
        config,
        "FACEBOOK_RESULT_FUTURE_GAMES_REPLY_TEXT",
        "You've been added to the follower list and will be part of future games soon.",
    )
).strip()
FACEBOOK_JOIN_KEYWORDS = _parse_keyword_list(
    os.getenv("FACEBOOK_JOIN_KEYWORDS"),
    default=getattr(config, "FACEBOOK_JOIN_KEYWORDS", ["join"]),
)
FACEBOOK_RESULT_KEYWORDS = _parse_keyword_list(
    os.getenv("FACEBOOK_RESULT_KEYWORDS"),
    default=getattr(config, "FACEBOOK_RESULT_KEYWORDS", ["result"]),
)
FACEBOOK_UPLOAD_JOIN_COMMENT_ENABLED = _parse_bool(
    os.getenv("FACEBOOK_UPLOAD_JOIN_COMMENT_ENABLED"),
    default=bool(getattr(config, "FACEBOOK_UPLOAD_JOIN_COMMENT_ENABLED", True)),
)
FACEBOOK_UPLOAD_JOIN_COMMENT_TEXT = str(
    os.getenv("FACEBOOK_UPLOAD_JOIN_COMMENT_TEXT")
    or getattr(
        config,
        "FACEBOOK_UPLOAD_JOIN_COMMENT_TEXT",
        'Comment "JOIN" in order to be added to future games',
    )
).strip()
YOUTUBE_ENABLE_JOIN_CAPTURE = _parse_bool(
    os.getenv("YOUTUBE_ENABLE_JOIN_CAPTURE"),
    default=bool(getattr(config, "YOUTUBE_ENABLE_JOIN_CAPTURE", True)),
)
YOUTUBE_ENABLE_RESULT_REPLIES = _parse_bool(
    os.getenv("YOUTUBE_ENABLE_RESULT_REPLIES"),
    default=bool(getattr(config, "YOUTUBE_ENABLE_RESULT_REPLIES", False)),
)
YOUTUBE_JOIN_KEYWORDS = _parse_keyword_list(
    os.getenv("YOUTUBE_JOIN_KEYWORDS"),
    default=getattr(config, "YOUTUBE_JOIN_KEYWORDS", ["join"]),
)
YOUTUBE_RESULT_KEYWORDS = _parse_keyword_list(
    os.getenv("YOUTUBE_RESULT_KEYWORDS"),
    default=getattr(config, "YOUTUBE_RESULT_KEYWORDS", ["result"]),
)
YOUTUBE_JOIN_ACK_REPLY_ENABLED = _parse_bool(
    os.getenv("YOUTUBE_JOIN_ACK_REPLY_ENABLED"),
    default=bool(getattr(config, "YOUTUBE_JOIN_ACK_REPLY_ENABLED", True)),
)
YOUTUBE_JOIN_ACK_REPLY_TEXT = str(
    os.getenv("YOUTUBE_JOIN_ACK_REPLY_TEXT")
    or getattr(config, "YOUTUBE_JOIN_ACK_REPLY_TEXT", "You're in. You'll be added to future games.")
).strip()
YOUTUBE_JOIN_ALREADY_REPLY_TEXT = str(
    os.getenv("YOUTUBE_JOIN_ALREADY_REPLY_TEXT")
    or getattr(
        config,
        "YOUTUBE_JOIN_ALREADY_REPLY_TEXT",
        'You are already part of the games. Comment "RESULT" to see how you did.',
    )
).strip()
YOUTUBE_RESULT_FUTURE_GAMES_REPLY_TEXT = str(
    os.getenv("YOUTUBE_RESULT_FUTURE_GAMES_REPLY_TEXT")
    or getattr(
        config,
        "YOUTUBE_RESULT_FUTURE_GAMES_REPLY_TEXT",
        "You've been added to the follower list and will be part of future games soon.",
    )
).strip()
YOUTUBE_COMMENT_POLL_ENABLED = _parse_bool(
    os.getenv("YOUTUBE_COMMENT_POLL_ENABLED"),
    default=bool(getattr(config, "YOUTUBE_COMMENT_POLL_ENABLED", False)),
)
YOUTUBE_COMMENT_POLL_INTERVAL_SECONDS = float(
    os.getenv(
        "YOUTUBE_COMMENT_POLL_INTERVAL_SECONDS",
        str(getattr(config, "YOUTUBE_COMMENT_POLL_INTERVAL_SECONDS", 90)),
    )
)
YOUTUBE_COMMENT_POLL_MAX_THREADS = int(
    os.getenv(
        "YOUTUBE_COMMENT_POLL_MAX_THREADS",
        str(getattr(config, "YOUTUBE_COMMENT_POLL_MAX_THREADS", 100)),
    )
)
YOUTUBE_ALLOW_INTERACTIVE_AUTH = _parse_bool(
    os.getenv("YOUTUBE_ALLOW_INTERACTIVE_AUTH"),
    default=bool(getattr(config, "YOUTUBE_ALLOW_INTERACTIVE_AUTH", False)),
)
YOUTUBE_CHANNEL_ID = (
    os.getenv("YOUTUBE_CHANNEL_ID")
    or getattr(config, "YOUTUBE_CHANNEL_ID", "")
).strip()

# Reply throttling / queueing (avoid IG reply blocks)
REPLY_RATE_MIN_SECONDS = float(os.getenv("WEBHOOK_REPLY_RATE_MIN_SECONDS", "4.0"))
REPLY_RATE_MAX_SECONDS = float(os.getenv("WEBHOOK_REPLY_RATE_MAX_SECONDS", "6.0"))
REPLY_BACKOFF_MIN_SECONDS = float(os.getenv("WEBHOOK_REPLY_BACKOFF_MIN_SECONDS", "30.0"))
REPLY_BACKOFF_MAX_SECONDS = float(os.getenv("WEBHOOK_REPLY_BACKOFF_MAX_SECONDS", "90.0"))
REPLY_MAX_RETRIES = int(os.getenv("WEBHOOK_REPLY_MAX_RETRIES", "2"))
REPLY_QUEUE_MAX = int(os.getenv("WEBHOOK_REPLY_QUEUE_MAX", "10000"))
IG_REPLY_BLOCK_SUBCODE = 1772107
REPLY_QUEUE_WARN_THRESHOLD = int(os.getenv("WEBHOOK_REPLY_QUEUE_WARN_THRESHOLD", "1000"))
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("WEBHOOK_HEARTBEAT_INTERVAL_SECONDS", "30"))

# Keywords that trigger auto-reply (case insensitive)
TRIGGER_KEYWORDS = [
    "result",
]

RESULTS_FOOTER = "To see other results like your monthly ranking check out the link in bio"
DISCORD_ONLY_GAMES = {
    "mingle",
    "lava_platform",
    "plinko",
    "discord_signal",
}
CLUB_ONLY_GAMES = {
    "club_duel",
    "club_relic",
}
DISCORD_ONLY_MESSAGE = (
    "You need to be part of the Discord Server to join this game. "
    "Check out the link in the bio to join"
)

RESULTS_MESSAGE_TEMPLATES = [
    "Your result in the {game_display} - Day {day_number}: {placement}\n{RESULTS_FOOTER}",
    "Result for {game_display} Day {day_number}: {placement}\n{RESULTS_FOOTER}",
    "Here's your {game_display} result (Day {day_number}): {placement}\n{RESULTS_FOOTER}",
]

NOT_FOLLOWING_TEMPLATES = [
    "You were not following during the making of this game, but you will be part of tomorrow's games if you are followed.\n{RESULTS_FOOTER}",
    "You weren't following when this game ran, but you can be included in tomorrow's games.\n{RESULTS_FOOTER}",
]

CLUB_NOT_MEMBER_TEMPLATES = [
    "You are not part of the Follower Battlegrounds Club. To join the next game, join the club from the link in the bio.",
    "You're not in the Follower Battlegrounds Club yet. Join via the link in bio to be in the next game.",
]

RESULTS_NOT_READY_TEMPLATES = [
    "Results for this game are not posted yet, but they should be up soon.\n{RESULTS_FOOTER}",
    "Results aren't available yet for this game - check back soon.\n{RESULTS_FOOTER}",
]

DISCORD_ONLY_MESSAGE_TEMPLATES = [
    DISCORD_ONLY_MESSAGE,
    "Discord-only game: join the Discord via the link in bio to participate.",
]

DISCORD_USERNAME_NOT_FOUND_TEMPLATES = [
    "We couldn't find that Discord username in the results. Please comment like: result: yourDiscordUsername\n{RESULTS_FOOTER}",
    "That Discord username wasn't found in today's results. Comment like: result: yourDiscordUsername\n{RESULTS_FOOTER}",
]

GAME_MODE_ALIASES = {
    "battle royale": "battle_royale",
    "battle_royale": "battle_royale",
    "fighter arena": "fighter_arena",
    "fighter_arena": "fighter_arena",
    "obstacle course": "obstacle_course",
    "obstacle_course": "obstacle_course",
    "snake escape": "snake_escape",
    "snake_escape": "snake_escape",
    "team battle": "team_battle",
    "team_battle": "team_battle",
    "platformer race": "platformer_race",
    "platformer_race": "platformer_race",
    "spleef": "spleef",
    "mingle": "mingle",
    "heads or tails": "heads_or_tails",
    "head or tails": "heads_or_tails",
    "heads/tails": "heads_or_tails",
    "heads_or_tails": "heads_or_tails",
    "wheel spinner": "wheel_spinner",
    "wheel_spinner": "wheel_spinner",
    "gorillas vs followers": "gorillas_vs_followers",
    "gorilla vs followers": "gorillas_vs_followers",
    "gorillas_vs_followers": "gorillas_vs_followers",
    "lava escape": "lava_platform",
    "lava platform": "lava_platform",
    "meteor mayhem": "meteor_mayhem",
    "meteor_mayhem": "meteor_mayhem",
    "anime fighting": "anime_fighting",
    "anime_fighting": "anime_fighting",
    "maze rush": "maze_rush",
    "maze_rush": "maze_rush",
    "beacon blitz": "beacon_blitz",
    "beacon_blitz": "beacon_blitz",
    "lane rush": "lane_rush",
    "lane_rush": "lane_rush",
    "math drop": "math_drop",
    "mathdrop": "math_drop",
    "math game": "math_drop",
    "math_drop": "math_drop",
    "plinko": "plinko",
    "mini golf": "mini_golf",
    "mini_golf": "mini_golf",
    "minigolf": "mini_golf",
    "mini-golf": "mini_golf",
    "flappy followers": "flappy_followers",
    "flappy follower": "flappy_followers",
    "flappy_followers": "flappy_followers",
    "flappy": "flappy_followers",
    "tiny followers": "tiny_followers",
    "tiny follower": "tiny_followers",
    "tiny_followers": "tiny_followers",
    "tiny wings": "tiny_followers",
    "tiny_wings": "tiny_followers",
    "jetpack followers": "jetpack_followers",
    "jetpack follower": "jetpack_followers",
    "jetpack_followers": "jetpack_followers",
    "jetpack": "jetpack_followers",
    "crossy followers": "crossy_followers",
    "crossy follower": "crossy_followers",
    "crossy_followers": "crossy_followers",
    "crossy": "crossy_followers",
    "followers.io": "followers_io",
    "followers io": "followers_io",
    "followers_io": "followers_io",
    "followersio": "followers_io",
    "agar": "followers_io",
    "agar.io": "followers_io",
    "agario": "followers_io",
    "subway followers": "subway_followers",
    "subway follower": "subway_followers",
    "subway_followers": "subway_followers",
    "subway": "subway_followers",
    "subway surfers": "subway_followers",
    "subway surfer": "subway_followers",
    "subway followers 3d": "subway_followers",
    "subway_followers_3d": "subway_followers",
    "discord signal": "discord_signal",
    "discord_signal": "discord_signal",
    "club duel": "club_duel",
    "club_duel": "club_duel",
    "club relic": "club_relic",
    "club_relic": "club_relic",
    "relic rally": "club_relic",
    "super follower bros": "super_follower_bros",
    "super follower bros.": "super_follower_bros",
    "super follower brothers": "super_follower_bros",
    "super_follower_bros": "super_follower_bros",
}

GAME_DISPLAY_NAMES = {
    "battle_royale": "Battle Royale",
    "fighter_arena": "Fighter Arena",
    "obstacle_course": "Obstacle Course",
    "snake_escape": "Snake Escape",
    "team_battle": "Team Battle",
    "platformer_race": "Platformer Race",
    "spleef": "Spleef",
    "mingle": "Mingle",
    "heads_or_tails": "Heads or Tails",
    "wheel_spinner": "Wheel Spinner",
    "gorillas_vs_followers": "Gorillas vs Followers",
    "meteor_mayhem": "Meteor Mayhem",
    "anime_fighting": "Anime Fighting",
    "maze_rush": "Maze Rush",
    "math_drop": "Math Drop",
    "plinko": "Plinko",
    "mini_golf": "Mini Golf",
    "lava_platform": "Lava Escape",
    "flappy_followers": "Flappy Followers",
    "tiny_followers": "Tiny Followers",
    "jetpack_followers": "Jetpack Followers",
    "crossy_followers": "Crossy Followers",
    "followers_io": "Followers.io",
    "doodle_followers": "Doodle Followers",
    "beacon_blitz": "Beacon Blitz",
    "lane_rush": "Lane Rush",
    "discord_signal": "Discord Signal",
    "club_duel": "Club Duel",
    "club_relic": "Relic Rally",
    "super_follower_bros": "Super Follower Bros.",
    "subway_followers": "Subway Followers",
}


def _looks_like_smb_mode(game_mode) -> bool:
    if not game_mode:
        return False
    return str(game_mode).lower().startswith("super_follower_bros")


def _normalize_smb_mode(game_mode):
    try:
        from super_follower_bros_shared.levels import normalize_smb_mode
    except Exception:
        return str(game_mode) if _looks_like_smb_mode(game_mode) else None
    return normalize_smb_mode(game_mode)


def _is_smb_mode(game_mode) -> bool:
    return _normalize_smb_mode(game_mode) is not None or _looks_like_smb_mode(game_mode)


def _is_jetpack_mode(game_mode) -> bool:
    return str(game_mode or "").strip().lower() == "jetpack_followers"


def _is_crossy_mode(game_mode) -> bool:
    return str(game_mode or "").strip().lower() == "crossy_followers"


def _base_mapping_source(mapping_source):
    source = str(mapping_source or "").strip().lower()
    if source.startswith("cache:"):
        source = source.split(":", 1)[1]
    return source


def _should_apply_day_offset(mapping_source, day_number, offset):
    """
    Apply mode day offset only when the mapped day came from caption-style metadata.
    Mapping sources derived from logs/timestamps already use actual day numbers.
    """
    source = _base_mapping_source(mapping_source)
    if source in {"caption", "recent_media"}:
        return True

    if source in {
        "upload_log_ts",
        "known_day_ts",
        "known_game_ts",
        "timestamp",
        "timestamp_relaxed",
        "recent_media_upload_log_ts",
        "recent_media_known_day_ts",
        "recent_media_known_game_ts",
    }:
        return False

    # Legacy/unknown source: avoid double-offset on large (already-actual) day values.
    try:
        return int(day_number) <= int(offset)
    except Exception:
        return False


def _smb_mode_candidates(game_mode):
    if not game_mode:
        return []
    raw_mode = str(game_mode)
    candidates = [raw_mode]
    normalized = _normalize_smb_mode(raw_mode)
    if normalized:
        candidates.append(normalized)
        if normalized == "super_follower_bros_1_1":
            candidates.append("super_follower_bros")
        if raw_mode == "super_follower_bros":
            candidates.append("super_follower_bros_1_1")
    if _looks_like_smb_mode(raw_mode) and raw_mode not in candidates:
        candidates.append(raw_mode)
    deduped = []
    seen = set()
    for value in candidates:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


def _smb_display_name(game_mode):
    if not _is_smb_mode(game_mode):
        return None
    try:
        from super_follower_bros_shared.levels import world_label_for_mode
    except Exception:
        return "Super Follower Bros."
    return f"Super Follower Bros. {world_label_for_mode(game_mode)}"


DATA_ROOT = BASE_DIR / "website" / "public" / "api"
_local_history_default = True
_local_history_override = getattr(config, "WEBHOOK_USE_LOCAL_HISTORY", None)
if _local_history_override is not None:
    _local_history_default = bool(_local_history_override)
WEBHOOK_USE_LOCAL_HISTORY = os.getenv(
    "WEBHOOK_USE_LOCAL_HISTORY",
    "1" if _local_history_default else "0",
).strip().lower() not in ("0", "false", "no")
WEBHOOK_LOCAL_HISTORY_FILE = os.getenv("WEBHOOK_LOCAL_HISTORY_FILE", "game_history.json").strip() or "game_history.json"

_LOCAL_HISTORY = None
_LOCAL_HISTORY_MTIME = None
_LOCAL_GAME_INDEX = {}
_LOCAL_DAY_INDEX = {}
_LOCAL_HISTORY_LOCK = threading.Lock()
REQUEST_TIMEOUT_SECONDS = 20
LOG_DIR = BASE_DIR / "logs" / "webhook_services"
QUEUE_STATE_PATH = LOG_DIR / "reply_queue_state.json"
QUEUE_EVENTS_PATH = LOG_DIR / "reply_queue_events.jsonl"
QUEUE_META_PATH = LOG_DIR / "reply_queue_meta.json"
HEARTBEAT_LOG_PATH = LOG_DIR / "instagram_webhook_heartbeat.log"
FACEBOOK_MEDIA_GAME_MAP_PATH = Path(
    os.getenv(
        "FACEBOOK_MEDIA_GAME_MAP_PATH",
        str(
            getattr(
                config,
                "FACEBOOK_MEDIA_GAME_MAP_PATH",
                LOG_DIR / "facebook_media_game_mapping.json",
            )
        ),
    )
)
if not FACEBOOK_MEDIA_GAME_MAP_PATH.is_absolute():
    FACEBOOK_MEDIA_GAME_MAP_PATH = BASE_DIR / FACEBOOK_MEDIA_GAME_MAP_PATH
YOUTUBE_MEDIA_GAME_MAP_PATH = Path(
    os.getenv(
        "YOUTUBE_MEDIA_GAME_MAP_PATH",
        str(
            getattr(
                config,
                "YOUTUBE_MEDIA_GAME_MAP_PATH",
                LOG_DIR / "youtube_media_game_mapping.json",
            )
        ),
    )
)
if not YOUTUBE_MEDIA_GAME_MAP_PATH.is_absolute():
    YOUTUBE_MEDIA_GAME_MAP_PATH = BASE_DIR / YOUTUBE_MEDIA_GAME_MAP_PATH
YOUTUBE_CLIENT_SECRET_PATH = Path(
    str(
        os.getenv("YOUTUBE_CLIENT_SECRET_PATH")
        or getattr(config, "YOUTUBE_CLIENT_SECRET_PATH", "secrets/youtube_client_secret.json")
        or "secrets/youtube_client_secret.json"
    ).strip()
)
if not YOUTUBE_CLIENT_SECRET_PATH.is_absolute():
    YOUTUBE_CLIENT_SECRET_PATH = BASE_DIR / YOUTUBE_CLIENT_SECRET_PATH
YOUTUBE_COMMENT_TOKEN_PATH = Path(
    str(
        os.getenv("YOUTUBE_COMMENT_TOKEN_PATH")
        or getattr(config, "YOUTUBE_COMMENT_TOKEN_PATH", "secrets/youtube_comment_token.pickle")
        or "secrets/youtube_comment_token.pickle"
    ).strip()
)
if not YOUTUBE_COMMENT_TOKEN_PATH.is_absolute():
    YOUTUBE_COMMENT_TOKEN_PATH = BASE_DIR / YOUTUBE_COMMENT_TOKEN_PATH
YOUTUBE_UPLOAD_TOKEN_PATH = Path(str(os.getenv("YOUTUBE_TOKEN_PATH", "secrets/youtube_token.json")).strip())
if not YOUTUBE_UPLOAD_TOKEN_PATH.is_absolute():
    YOUTUBE_UPLOAD_TOKEN_PATH = BASE_DIR / YOUTUBE_UPLOAD_TOKEN_PATH
PROCESSED_COMMENT_IDS_PATH = Path(
    os.getenv(
        "FACEBOOK_PROCESSED_COMMENT_IDS_PATH",
        str(
            getattr(
                config,
                "FACEBOOK_PROCESSED_COMMENT_IDS_PATH",
                LOG_DIR / "processed_comment_ids.json",
            )
        ),
    )
)
if not PROCESSED_COMMENT_IDS_PATH.is_absolute():
    PROCESSED_COMMENT_IDS_PATH = BASE_DIR / PROCESSED_COMMENT_IDS_PATH
PROCESSED_COMMENT_IDS_MAX = int(os.getenv("FACEBOOK_PROCESSED_COMMENT_IDS_MAX", "50000"))
FOLLOWER_STORE_PATH = Path(getattr(config, "FOLLOWER_IMPORT_FILE", "Followers/new_followers_fresh.json"))
if not FOLLOWER_STORE_PATH.is_absolute():
    FOLLOWER_STORE_PATH = BASE_DIR / FOLLOWER_STORE_PATH
MEDIA_GAME_MAP_PATH = Path(
    os.getenv("WEBHOOK_MEDIA_GAME_MAP_PATH", str(LOG_DIR / "media_game_mapping.json"))
)
MEDIA_GAME_MAP_MAX_ENTRIES = int(os.getenv("WEBHOOK_MEDIA_GAME_MAP_MAX_ENTRIES", "5000"))
MEDIA_TS_MATCH_MAX_HOURS = float(os.getenv("WEBHOOK_MEDIA_TS_MATCH_MAX_HOURS", "30"))
MEDIA_TS_AMBIGUITY_MIN_GAP_SECONDS = int(
    os.getenv("WEBHOOK_MEDIA_TS_AMBIGUITY_MIN_GAP_SECONDS", "900")
)
NEARBY_DAY_FALLBACK_RADIUS = int(os.getenv("WEBHOOK_NEARBY_DAY_FALLBACK_RADIUS", "3"))
MEDIA_BACKFILL_ON_MISS = os.getenv("WEBHOOK_MEDIA_BACKFILL_ON_MISS", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
MEDIA_BACKFILL_LIMIT = int(os.getenv("WEBHOOK_MEDIA_BACKFILL_LIMIT", "50"))
MEDIA_BACKFILL_MAX_PAGES = int(os.getenv("WEBHOOK_MEDIA_BACKFILL_MAX_PAGES", "3"))
MEDIA_BACKFILL_MIN_INTERVAL_SECONDS = float(
    os.getenv("WEBHOOK_MEDIA_BACKFILL_MIN_INTERVAL_SECONDS", "120")
)
UPLOAD_LOG_FALLBACK_ON_MISS = os.getenv("WEBHOOK_UPLOAD_LOG_FALLBACK_ON_MISS", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
UPLOAD_LOG_DIR = BASE_DIR / "logs" / "scheduled_upload"
UPLOAD_LOG_MAX_FILES = int(os.getenv("WEBHOOK_UPLOAD_LOG_MAX_FILES", "14"))
UPLOAD_LOG_MATCH_MAX_MINUTES = float(os.getenv("WEBHOOK_UPLOAD_LOG_MATCH_MAX_MINUTES", "25"))
UPLOAD_LOG_TIMEZONE = os.getenv("WEBHOOK_UPLOAD_LOG_TIMEZONE", "Europe/Oslo").strip() or "Europe/Oslo"

# ============== WEBHOOK ENDPOINTS ==============

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Handle Meta's webhook verification request"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    print(f"Verification request - Mode: {mode}, Token: {token}")

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        print(f"Verification failed. Expected token: {VERIFY_TOKEN}, Got: {token}")
        return 'Forbidden', 403


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming webhook events (comments, mentions, etc.)"""
    data = request.get_json() or {}
    print("\n" + "=" * 50)
    print("Received webhook event:")
    print(json.dumps(data, indent=2))
    print("=" * 50 + "\n")

    try:
        object_type = str(data.get("object") or "").strip().lower()

        # Process each entry in the webhook payload
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                field = change.get('field')
                value = change.get('value', {})

                if object_type == "page":
                    handle_page_change(field, value)
                    continue

                if field == 'comments':
                    handle_comment(value)
                elif field == 'mentions':
                    handle_mention(value)
                elif field == 'messages':
                    handle_message(value)

    except Exception as e:
        print(f"Error processing webhook: {e}")

    return jsonify({'status': 'ok'}), 200


# ============== EVENT HANDLERS ==============

def handle_comment(comment_data):
    """Process a new comment and potentially post an auto-reply"""
    comment_text = comment_data.get('text')
    comment_id = comment_data.get('id')
    commenter_id = comment_data.get('from', {}).get('id')
    commenter_username = comment_data.get('from', {}).get('username', 'Unknown')

    if commenter_id and str(commenter_id) == str(INSTAGRAM_ACCOUNT_ID):
        print("Skipping comment from our own account")
        return

    if not comment_text and comment_id:
        comment_text = fetch_comment_text(comment_id)

    comment_text_lower = (comment_text or "").lower()
    print(f"New comment from @{commenter_username}: {comment_text_lower}")

    if not comment_id:
        print("Missing comment id - reply skipped")
        return

    dedupe_key = f"instagram:{comment_id}"
    if not _claim_comment_processing(dedupe_key):
        print(f"Skipping duplicate IG comment event: {comment_id}")
        return

    marked_processed = False
    try:
        # Check if comment contains trigger keyword
        if any(keyword.lower() in comment_text_lower for keyword in TRIGGER_KEYWORDS):
            print(f"Trigger keyword detected. Queueing reply to @{commenter_username}")
            message = build_results_message(comment_data, comment_text)
            queued = enqueue_reply(
                comment_id,
                message,
                platform="instagram",
                access_token=INSTAGRAM_ACCESS_TOKEN_APP,
            )
            if queued:
                _mark_comment_processed(
                    dedupe_key,
                    {
                        "platform": "instagram",
                        "trigger": True,
                    },
                )
                marked_processed = True
        else:
            print("No trigger keyword found in comment")
            _mark_comment_processed(
                dedupe_key,
                {
                    "platform": "instagram",
                    "trigger": False,
                },
            )
            marked_processed = True
    finally:
        if not marked_processed:
            _release_comment_claim(dedupe_key)


def handle_mention(mention_data):
    """Process when someone mentions the account"""
    print(f"New mention: {mention_data}")


def handle_message(message_data):
    """Process incoming DMs (for future use)"""
    print(f"New message: {message_data}")


def _normalize_whitespace(text):
    return re.sub(r"\s+", " ", str(text or "").strip())


def _extract_facebook_post_id(value):
    if not isinstance(value, dict):
        return ""
    post_payload = value.get("post") if isinstance(value.get("post"), dict) else {}
    for candidate in (
        value.get("post_id"),
        post_payload.get("id"),
        value.get("parent_id"),
    ):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def _facebook_post_has_comment(post_id, expected_message):
    post_ref = str(post_id or "").strip()
    expected = _normalize_whitespace(expected_message).lower()
    if not post_ref or not expected or not str(FACEBOOK_PAGE_ACCESS_TOKEN or "").strip():
        return False

    version = str(FACEBOOK_GRAPH_API_VERSION or "v18.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{version}/{post_ref}/comments"
    params = {
        "fields": "id,message,from{id,name}",
        "filter": "stream",
        "limit": 50,
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except Exception as exc:
        print(f"Failed to read FB comments for {post_ref}: {exc}")
        return False

    if not response.ok:
        print(f"Failed to read FB comments for {post_ref}: HTTP {response.status_code} {response.text[:300]}")
        return False

    try:
        payload = response.json()
    except Exception:
        return False
    for item in payload.get("data", []) if isinstance(payload, dict) else []:
        message_norm = _normalize_whitespace(item.get("message")).lower()
        if message_norm != expected:
            continue
        from_payload = item.get("from") if isinstance(item.get("from"), dict) else {}
        from_id = str(from_payload.get("id") or "").strip()
        if FACEBOOK_PAGE_ID and from_id and from_id != str(FACEBOOK_PAGE_ID):
            continue
        return True
    return False


def _post_facebook_comment_on_target(target_id, message):
    target_ref = str(target_id or "").strip()
    payload_text = str(message or "").strip()
    if not target_ref or not payload_text:
        return False
    if not str(FACEBOOK_PAGE_ACCESS_TOKEN or "").strip():
        print(f"FB JOIN CTA comment skipped (missing page token) for {target_ref}")
        return False

    version = str(FACEBOOK_GRAPH_API_VERSION or "v18.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{version}/{target_ref}/comments"
    payload = {
        "message": payload_text,
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    try:
        response = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    except Exception as exc:
        print(f"FB JOIN CTA comment request failed for {target_ref}: {exc}")
        return False
    if response.status_code == 200:
        return True
    print(f"FB JOIN CTA comment failed for {target_ref}: HTTP {response.status_code} {response.text[:300]}")
    return False


def _maybe_post_facebook_join_prompt_for_new_video(value):
    if not FACEBOOK_UPLOAD_JOIN_COMMENT_ENABLED:
        return

    prompt_text = str(FACEBOOK_UPLOAD_JOIN_COMMENT_TEXT or "").strip()
    if not prompt_text:
        return

    if not isinstance(value, dict):
        return

    post_id = _extract_facebook_post_id(value)
    if not post_id:
        return

    if str(value.get("comment_id") or "").strip():
        return

    item = str(value.get("item") or "").strip().lower()
    verb = str(value.get("verb") or "").strip().lower()
    post_payload = value.get("post") if isinstance(value.get("post"), dict) else {}
    status_type = str(post_payload.get("status_type") or value.get("status_type") or "").strip().lower()
    if verb and verb not in {"add", "create"}:
        return
    if status_type != "added_video" and item != "video":
        return

    from_payload = value.get("from") if isinstance(value.get("from"), dict) else {}
    author_id = str(from_payload.get("id") or "").strip()
    if author_id and FACEBOOK_PAGE_ID and author_id != str(FACEBOOK_PAGE_ID):
        return

    dedupe_key = f"facebook_join_prompt_post:{post_id}"
    if _is_comment_processed(dedupe_key):
        return

    if _facebook_post_has_comment(post_id, prompt_text):
        print(f"FB JOIN CTA already exists on {post_id}")
        _mark_comment_processed(
            dedupe_key,
            {"platform": "facebook", "type": "join_prompt_comment", "post_id": post_id, "status": "already_exists"},
        )
        return

    if _post_facebook_comment_on_target(post_id, prompt_text):
        print(f"FB JOIN CTA posted on new video post {post_id}")
        _mark_comment_processed(
            dedupe_key,
            {"platform": "facebook", "type": "join_prompt_comment", "post_id": post_id, "status": "posted"},
        )
    else:
        print(f"FB JOIN CTA could not be posted on {post_id}")


def handle_page_change(field, value):
    """Handle Facebook Page webhook change payloads."""
    if not isinstance(value, dict):
        return
    field_name = str(field or "").strip().lower()
    if field_name not in {"feed", "comments"}:
        return

    if field_name == "feed":
        _maybe_post_facebook_join_prompt_for_new_video(value)

    item = str(value.get("item") or "").strip().lower()
    verb = str(value.get("verb") or "").strip().lower()
    if item and item != "comment":
        return
    if verb and verb not in {"add", "create"}:
        return

    comment_id = value.get("comment_id") or value.get("id")
    if not comment_id:
        return

    from_payload = value.get("from") if isinstance(value.get("from"), dict) else {}
    commenter_id = str(from_payload.get("id") or "").strip()
    commenter_name = str(
        from_payload.get("name")
        or from_payload.get("username")
        or value.get("sender_name")
        or "Facebook User"
    ).strip()

    normalized = {
        "id": str(comment_id).strip(),
        "text": value.get("message") or value.get("text") or "",
        "from": {
            "id": commenter_id,
            "name": commenter_name,
        },
        "post_id": str(value.get("post_id") or "").strip(),
        "parent_id": str(value.get("parent_id") or "").strip(),
        "created_time": value.get("created_time"),
        "raw": value,
    }

    handle_facebook_comment(normalized)


def handle_facebook_comment(comment_data):
    """Process Facebook Page comment for JOIN intake and RESULT replies."""
    comment_id = str(comment_data.get("id") or "").strip()
    if not comment_id:
        print("Skipping FB comment without id")
        return

    from_data = comment_data.get("from") if isinstance(comment_data.get("from"), dict) else {}
    commenter_id = str(from_data.get("id") or "").strip()
    commenter_name = str(from_data.get("name") or "Facebook User").strip()

    if commenter_id and FACEBOOK_PAGE_ID and commenter_id == str(FACEBOOK_PAGE_ID):
        print("Skipping FB comment from own page")
        return

    dedupe_key = f"facebook:{comment_id}"
    if not _claim_comment_processing(dedupe_key):
        print(f"Skipping duplicate FB comment event: {comment_id}")
        return

    marked_processed = False
    try:
        comment_text = str(comment_data.get("text") or "").strip()
        if not comment_text:
            comment_text = str(fetch_facebook_comment_text(comment_id) or "").strip()
        if not comment_data.get("post_id") or not comment_data.get("created_time"):
            comment_meta = fetch_facebook_object_metadata(comment_id)
            if comment_meta:
                if not comment_data.get("post_id"):
                    comment_data["post_id"] = str(comment_meta.get("post_id") or "").strip()
                if not comment_data.get("parent_id"):
                    comment_data["parent_id"] = str(comment_meta.get("parent_id") or "").strip()
                if not comment_data.get("created_time"):
                    comment_data["created_time"] = comment_meta.get("created_time")
                if not comment_text:
                    comment_text = str(comment_meta.get("message") or "").strip()
        comment_text_lower = comment_text.lower()
        print(f"New Facebook comment from '{commenter_name}' ({commenter_id or 'no-id'}): {comment_text_lower}")

        has_join = FACEBOOK_ENABLE_JOIN_CAPTURE and _contains_keyword_word(comment_text_lower, FACEBOOK_JOIN_KEYWORDS)
        has_result = FACEBOOK_ENABLE_RESULT_REPLIES and _contains_keyword_word(comment_text_lower, FACEBOOK_RESULT_KEYWORDS)

        join_result = None
        if has_join:
            if upsert_facebook_join is None:
                print("FB JOIN helpers unavailable; skipping JOIN capture")
            else:
                try:
                    join_result = upsert_facebook_join(
                        FOLLOWER_STORE_PATH,
                        facebook_user_id=commenter_id or None,
                        facebook_name=commenter_name or None,
                        comment_id=comment_id,
                        post_id=comment_data.get("post_id") or comment_data.get("parent_id"),
                    )
                    if join_result and join_result.get("ok"):
                        _invalidate_follower_username_cache()
                        print(
                            f"FB JOIN stored: {join_result.get('status')} | "
                            f"@{join_result.get('username')} | total={join_result.get('total_followers')}"
                        )
                    else:
                        print("FB JOIN processing returned no result")
                except Exception as exc:
                    print(f"FB JOIN processing failed: {exc}")

        reply_message = None
        if has_result:
            reply_message = build_facebook_results_message(comment_data, comment_text)
        elif has_join and FACEBOOK_JOIN_ACK_REPLY_ENABLED:
            join_status = str((join_result or {}).get("status") or "").strip().lower()
            if join_status.startswith("updated_"):
                reply_message = FACEBOOK_JOIN_ALREADY_REPLY_TEXT
            else:
                reply_message = FACEBOOK_JOIN_ACK_REPLY_TEXT

        queued = False
        if reply_message:
            queued = enqueue_reply(
                comment_id=comment_id,
                message=reply_message,
                platform="facebook",
                access_token=FACEBOOK_PAGE_ACCESS_TOKEN,
            )

        if reply_message and not queued:
            print(f"FB reply could not be queued for comment {comment_id}")
            return

        _mark_comment_processed(
            dedupe_key,
            {
                "platform": "facebook",
                "has_join": bool(has_join),
                "has_result": bool(has_result),
                "queued_reply": bool(queued),
            },
        )
        marked_processed = True
    finally:
        if not marked_processed:
            _release_comment_claim(dedupe_key)


def handle_youtube_comment(comment_data):
    """Process YouTube top-level comment for JOIN intake and RESULT replies."""
    comment_id = str(comment_data.get("id") or "").strip()
    if not comment_id:
        return

    dedupe_key = f"youtube:{comment_id}"
    if not _claim_comment_processing(dedupe_key):
        return

    from_data = comment_data.get("from") if isinstance(comment_data.get("from"), dict) else {}
    commenter_id = str(from_data.get("id") or "").strip()
    commenter_name = str(from_data.get("name") or "YouTube User").strip()
    own_channel_id = _resolve_youtube_channel_id()
    marked_processed = False
    try:
        if commenter_id and own_channel_id and commenter_id == own_channel_id:
            _mark_comment_processed(
                dedupe_key,
                {"platform": "youtube", "ignored_reason": "own_channel_comment"},
            )
            marked_processed = True
            return

        comment_text = str(comment_data.get("text") or "").strip()
        comment_text_lower = comment_text.lower()
        has_join = YOUTUBE_ENABLE_JOIN_CAPTURE and _contains_keyword_word(comment_text_lower, YOUTUBE_JOIN_KEYWORDS)
        has_result = YOUTUBE_ENABLE_RESULT_REPLIES and _contains_keyword_word(comment_text_lower, YOUTUBE_RESULT_KEYWORDS)

        join_result = None
        if has_join:
            if upsert_youtube_join is None:
                print("YouTube JOIN helpers unavailable; skipping JOIN capture")
            else:
                try:
                    join_result = upsert_youtube_join(
                        FOLLOWER_STORE_PATH,
                        youtube_channel_id=commenter_id or None,
                        youtube_display_name=commenter_name or None,
                        comment_id=comment_id,
                        video_id=comment_data.get("video_id"),
                    )
                    if join_result and join_result.get("ok"):
                        _invalidate_follower_username_cache()
                        print(
                            f"YouTube JOIN stored: {join_result.get('status')} | "
                            f"@{join_result.get('username')} | total={join_result.get('total_followers')}"
                        )
                except Exception as exc:
                    print(f"YouTube JOIN processing failed: {exc}")

        reply_message = None
        if has_result:
            reply_message = build_youtube_results_message(comment_data, comment_text)
        elif has_join and YOUTUBE_JOIN_ACK_REPLY_ENABLED:
            join_status = str((join_result or {}).get("status") or "").strip().lower()
            if join_status.startswith("updated_"):
                reply_message = YOUTUBE_JOIN_ALREADY_REPLY_TEXT
            else:
                reply_message = YOUTUBE_JOIN_ACK_REPLY_TEXT

        queued = False
        if reply_message:
            queued = enqueue_reply(
                comment_id=comment_id,
                message=reply_message,
                platform="youtube",
                access_token="youtube_oauth",
            )

        if reply_message and not queued:
            print(f"YouTube reply could not be queued for comment {comment_id}")
            return

        _mark_comment_processed(
            dedupe_key,
            {
                "platform": "youtube",
                "has_join": bool(has_join),
                "has_result": bool(has_result),
                "queued_reply": bool(queued),
            },
        )
        marked_processed = True
    finally:
        if not marked_processed:
            _release_comment_claim(dedupe_key)


def _poll_youtube_comments_once():
    youtube = _get_youtube_client(allow_interactive=False)
    if youtube is None:
        return 0

    channel_id = _resolve_youtube_channel_id(youtube)
    if not channel_id:
        return 0

    total = 0
    max_threads = max(1, int(YOUTUBE_COMMENT_POLL_MAX_THREADS))
    page_token = None
    remaining = max_threads

    while remaining > 0:
        batch_size = min(100, remaining)
        try:
            response = youtube.commentThreads().list(
                part="snippet",
                allThreadsRelatedToChannelId=channel_id,
                order="time",
                maxResults=batch_size,
                pageToken=page_token,
                textFormat="plainText",
            ).execute()
        except Exception as exc:
            print(f"YouTube comment poll request failed: {exc}")
            break

        items = response.get("items") if isinstance(response, dict) else []
        if not isinstance(items, list) or not items:
            break

        for item in items:
            thread_snippet = item.get("snippet") if isinstance(item, dict) else {}
            top_comment = thread_snippet.get("topLevelComment") if isinstance(thread_snippet, dict) else {}
            top_snippet = top_comment.get("snippet") if isinstance(top_comment, dict) else {}
            if not isinstance(top_snippet, dict):
                continue
            comment_id = str(top_comment.get("id") or "").strip()
            if not comment_id:
                continue
            author_payload = top_snippet.get("authorChannelId")
            if isinstance(author_payload, dict):
                author_channel_id = str(author_payload.get("value") or "").strip()
            else:
                author_channel_id = ""
            normalized = {
                "id": comment_id,
                "text": top_snippet.get("textDisplay") or top_snippet.get("textOriginal") or "",
                "video_id": str(top_snippet.get("videoId") or thread_snippet.get("videoId") or "").strip(),
                "published_at": top_snippet.get("publishedAt"),
                "from": {
                    "id": author_channel_id,
                    "name": str(top_snippet.get("authorDisplayName") or "YouTube User").strip(),
                },
                "raw": item,
            }
            handle_youtube_comment(normalized)
            total += 1

        remaining -= len(items)
        page_token = response.get("nextPageToken") if isinstance(response, dict) else None
        if not page_token:
            break

    return total


def _start_youtube_comment_poller_if_needed():
    global _YOUTUBE_POLLER_STARTED
    if _YOUTUBE_POLLER_STARTED:
        return
    if not _youtube_poller_enabled():
        return
    youtube = _get_youtube_client(allow_interactive=YOUTUBE_ALLOW_INTERACTIVE_AUTH)
    if youtube is None:
        print("WARNING: YouTube comment poller not started (missing OAuth/token).")
        return
    channel_id = _resolve_youtube_channel_id(youtube)
    if not channel_id:
        print("WARNING: YouTube comment poller not started (channel id not resolved).")
        return
    try:
        youtube.commentThreads().list(
            part="snippet",
            allThreadsRelatedToChannelId=channel_id,
            order="time",
            maxResults=1,
            textFormat="plainText",
        ).execute()
    except Exception as exc:
        print(f"WARNING: YouTube comment poller not started (permission check failed): {exc}")
        return

    _YOUTUBE_POLLER_STARTED = True

    def _run():
        interval = max(15.0, float(YOUTUBE_COMMENT_POLL_INTERVAL_SECONDS))
        print(
            f"YouTube comment poller started (channel={channel_id}, interval={interval:.0f}s, "
            f"max_threads={max(1, int(YOUTUBE_COMMENT_POLL_MAX_THREADS))})"
        )
        while True:
            try:
                scanned = _poll_youtube_comments_once()
                if scanned:
                    print(f"YouTube poll scanned {scanned} comment threads")
            except Exception as exc:
                print(f"YouTube comment poller error: {exc}")
            time.sleep(interval)

    thread = threading.Thread(target=_run, name="youtube-comment-poller", daemon=True)
    thread.start()


# ============== RESULTS LOGIC ==============

def normalize_game_mode(raw_value):
    if not raw_value:
        return None
    candidate = raw_value.strip().lower()
    if candidate in GAME_MODE_ALIASES:
        return GAME_MODE_ALIASES[candidate]
    smb_mode = _normalize_smb_mode(candidate)
    if smb_mode:
        return smb_mode
    candidate = candidate.replace("_", " ").replace("-", " ")
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if candidate in GAME_MODE_ALIASES:
        return GAME_MODE_ALIASES[candidate]
    underscored = candidate.replace(" ", "_")
    if underscored in GAME_MODE_ALIASES:
        return GAME_MODE_ALIASES[underscored]
    smb_mode = _normalize_smb_mode(underscored)
    if smb_mode:
        return smb_mode
    if underscored in GAME_DISPLAY_NAMES:
        return underscored
    return None


def parse_game_info(caption):
    if not caption:
        return None, None

    raw_game = None
    raw_day = None

    # Accept multiple caption styles:
    # - "Game: snake_escape | Day 78"
    # - "Game Mode: Snake Escape"
    game_day_patterns = [
        r"\bgame(?:\s*mode)?\s*[:\-]\s*([^\n\r|#]+?)\s*\|\s*day\s*[:#\-]?\s*(\d{1,4})\b",
        r"\bmode\s*[:\-]\s*([^\n\r|#]+?)\s*\|\s*day\s*[:#\-]?\s*(\d{1,4})\b",
    ]
    for pattern in game_day_patterns:
        game_day_match = re.search(pattern, caption, re.IGNORECASE)
        if game_day_match:
            raw_game = game_day_match.group(1).strip(" \t\r\n|#:-")
            raw_day = game_day_match.group(2)
            break

    game_patterns = [
        r"\bgame(?:\s*mode)?\s*[:\-]\s*([^\n\r|#]+)",
        r"\bmode\s*[:\-]\s*([^\n\r|#]+)",
    ]
    if raw_game is None:
        for pattern in game_patterns:
            game_match = re.search(pattern, caption, re.IGNORECASE)
            if game_match:
                raw_game = game_match.group(1).strip(" \t\r\n|#:-")
                break

    day_patterns = [
        r"\bday\s*[:#\-]?\s*(\d{1,4})\b",
        r"#day\s*(\d{1,4})\b",
    ]
    if raw_day is None:
        for pattern in day_patterns:
            day_matches = re.findall(pattern, caption, re.IGNORECASE)
            if day_matches:
                # Captions often include an intro day phrase before metadata;
                # prefer the final day mention in the caption.
                raw_day = day_matches[-1]
                break

    game_type = normalize_game_mode(raw_game)
    day_number = int(raw_day) if raw_day and raw_day.isdigit() else None

    return game_type, day_number


def _extract_day_number_from_text(text):
    body = str(text or "")
    if not body:
        return None
    matches = re.findall(r"\bday\s*[:#\-]?\s*(\d{1,4})\b", body, re.IGNORECASE)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except Exception:
        return None


def _extract_game_mode_from_youtube_title(title):
    text = str(title or "").strip()
    if not text:
        return None

    lower_text = text.lower()
    patterns = [
        r"\bfollower\s+(.+?)\s*-\s*day\b",
        r"^(.+?)\s*-\s*day\s*\d{1,4}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        candidate = str(match.group(1) or "").strip()
        candidate = re.sub(r"^\s*follower\s+", "", candidate, flags=re.IGNORECASE)
        candidate = candidate.split("|", 1)[0].strip()
        normalized = normalize_game_mode(candidate)
        if normalized:
            return normalized

    for game_mode, display_name in GAME_DISPLAY_NAMES.items():
        if str(display_name or "").strip().lower() in lower_text:
            return game_mode

    return None


def load_json_file(path):
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        print(f"Failed to load {path}: {exc}")
        return None


def _local_history_path() -> Path:
    path = Path(WEBHOOK_LOCAL_HISTORY_FILE)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _load_local_history() -> dict:
    global _LOCAL_HISTORY, _LOCAL_HISTORY_MTIME, _LOCAL_GAME_INDEX, _LOCAL_DAY_INDEX
    path = _local_history_path()
    if not path.exists():
        return {"games": []}

    try:
        mtime = path.stat().st_mtime
    except Exception:
        mtime = None

    if _LOCAL_HISTORY is not None and _LOCAL_HISTORY_MTIME == mtime:
        return _LOCAL_HISTORY

    with _LOCAL_HISTORY_LOCK:
        if _LOCAL_HISTORY is not None and _LOCAL_HISTORY_MTIME == mtime:
            return _LOCAL_HISTORY

        payload = load_json_file(path)
        if not isinstance(payload, dict):
            payload = {"games": []}
        if "games" not in payload or not isinstance(payload.get("games"), list):
            payload["games"] = []

        _LOCAL_HISTORY = payload
        _LOCAL_HISTORY_MTIME = mtime
        _LOCAL_GAME_INDEX = {}
        _LOCAL_DAY_INDEX = {}
        for game in payload.get("games", []):
            if not isinstance(game, dict):
                continue
            game_id = game.get("game_id")
            if game_id:
                _LOCAL_GAME_INDEX[game_id] = game
            day_number = game.get("day_number")
            if isinstance(day_number, str) and day_number.isdigit():
                day_number = int(day_number)
            if isinstance(day_number, int):
                _LOCAL_DAY_INDEX.setdefault(day_number, []).append(game)

        _DAY_SUMMARY_CACHE.clear()
        return _LOCAL_HISTORY


def _build_day_summary_from_history(day_number: int) -> dict | None:
    history = _load_local_history()
    if not history:
        return None
    games = _LOCAL_DAY_INDEX.get(int(day_number)) or []
    if not games:
        return None
    day_games = []
    for game in games:
        if not isinstance(game, dict):
            continue
        game_id = game.get("game_id")
        game_type = game.get("game_type")
        if not game_id or not game_type:
            continue
        day_games.append({
            "game_id": game_id,
            "game_type": game_type,
            "game_display_name": game.get("game_display_name"),
            "timestamp": game.get("timestamp"),
            "total_participants": game.get("total_participants") or len(game.get("results", []) or []),
            "non_scoring": game.get("non_scoring", False),
        })
    if not day_games:
        return None
    return {
        "day_number": int(day_number),
        "total_games": len(day_games),
        "games": day_games,
    }


def load_day_summary(day_number):
    if not day_number:
        return None
    key = int(day_number)
    if key in _DAY_SUMMARY_CACHE:
        return _DAY_SUMMARY_CACHE[key]
    payload = None
    if WEBHOOK_USE_LOCAL_HISTORY:
        payload = _build_day_summary_from_history(key)
    if payload is None:
        payload = load_json_file(DATA_ROOT / "days" / f"{key}.json")
    _DAY_SUMMARY_CACHE[key] = payload
    return payload


def find_game_entry(day_summary, game_type):
    if not day_summary or not game_type:
        return None
    game_candidates = set(_smb_mode_candidates(game_type))
    if not game_candidates:
        game_candidates = {game_type}
    matches = [
        game for game in day_summary.get("games", [])
        if game.get("game_type") in game_candidates
    ]
    if not matches:
        return None
    return max(matches, key=lambda game: game.get("timestamp", ""))


def _parse_timestamp(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # Meta often returns +0000 (without colon), normalize to +00:00
    if len(text) >= 5 and (text[-5] in "+-") and text[-3] != ":":
        text = text[:-2] + ":" + text[-2:]
    try:
        parsed = datetime.fromisoformat(text)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_media_game_map():
    global _MEDIA_GAME_MAP_LOADED, _MEDIA_GAME_MAP
    if _MEDIA_GAME_MAP_LOADED:
        return
    _MEDIA_GAME_MAP_LOADED = True
    _MEDIA_GAME_MAP = OrderedDict()
    data = load_json_file(MEDIA_GAME_MAP_PATH)
    if not isinstance(data, dict):
        return
    for media_id, payload in data.items():
        if not isinstance(payload, dict):
            continue
        game_type = normalize_game_mode(payload.get("game_type"))
        day_number = payload.get("day_number")
        if not game_type:
            continue
        try:
            day_number = int(day_number)
        except Exception:
            continue
        _MEDIA_GAME_MAP[str(media_id)] = {
            "game_type": game_type,
            "day_number": day_number,
            "source": payload.get("source", "cache"),
            "updated_at": payload.get("updated_at"),
        }


def _save_media_game_map():
    _ensure_log_dir()
    try:
        MEDIA_GAME_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            key: {
                "game_type": value.get("game_type"),
                "day_number": value.get("day_number"),
                "source": value.get("source", "cache"),
                "updated_at": value.get("updated_at"),
            }
            for key, value in _MEDIA_GAME_MAP.items()
        }
        with MEDIA_GAME_MAP_PATH.open("w", encoding="utf-8") as handle:
            json.dump(serializable, handle, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"Failed to save media mapping cache: {exc}")


def _lookup_media_mapping(media_id):
    if not media_id:
        return None
    _load_media_game_map()
    key = str(media_id)
    payload = _MEDIA_GAME_MAP.get(key)
    if not payload:
        return None
    # Refresh LRU ordering
    _MEDIA_GAME_MAP.move_to_end(key)
    return payload


def _remember_media_mapping(media_id, game_type, day_number, source):
    if not media_id or not game_type or not day_number:
        return
    _load_media_game_map()
    key = str(media_id)
    _MEDIA_GAME_MAP[key] = {
        "game_type": str(game_type),
        "day_number": int(day_number),
        "source": source,
        "updated_at": int(time.time()),
    }
    _MEDIA_GAME_MAP.move_to_end(key)
    while len(_MEDIA_GAME_MAP) > MEDIA_GAME_MAP_MAX_ENTRIES:
        _MEDIA_GAME_MAP.popitem(last=False)
    _save_media_game_map()


def _fetch_recent_media_for_mapping(limit: int, max_pages: int):
    if INSTAGRAM_ACCESS_TOKEN_APP == "YOUR_ACCESS_TOKEN_HERE":
        return []
    if INSTAGRAM_ACCOUNT_ID == "YOUR_ACCOUNT_ID_HERE":
        return []

    target_limit = max(1, min(int(limit), 200))
    pages_left = max(1, int(max_pages))
    fields = "id,caption,timestamp,media_product_type,permalink"
    page_limit = max(5, min(100, target_limit))

    url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": fields,
        "limit": page_limit,
        "access_token": INSTAGRAM_ACCESS_TOKEN_APP,
    }
    items = []

    while url and pages_left > 0 and len(items) < target_limit:
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code != 200:
                print(f"Failed to fetch media list: {response.status_code} - {response.text}")
                break
            payload = response.json()
        except Exception as exc:
            print(f"Error fetching media list: {exc}")
            break

        page_items = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(page_items, list):
            page_items = []

        for item in page_items:
            if isinstance(item, dict):
                items.append(item)
                if len(items) >= target_limit:
                    break

        paging = payload.get("paging", {}) if isinstance(payload, dict) else {}
        url = paging.get("next")
        params = None  # Next link already contains query params.
        pages_left -= 1

    return items[:target_limit]


def _backfill_media_mapping_from_recent_media(force: bool = False):
    global _LAST_MEDIA_BACKFILL_AT

    if not force and not MEDIA_BACKFILL_ON_MISS:
        return 0

    with _MEDIA_BACKFILL_LOCK:
        now = time.time()
        if not force and (now - _LAST_MEDIA_BACKFILL_AT) < MEDIA_BACKFILL_MIN_INTERVAL_SECONDS:
            return 0
        _LAST_MEDIA_BACKFILL_AT = now

        items = _fetch_recent_media_for_mapping(MEDIA_BACKFILL_LIMIT, MEDIA_BACKFILL_MAX_PAGES)
        if not items:
            return 0

        _load_media_game_map()
        changed = False
        mapped = 0
        updated_at = int(time.time())

        for item in items:
            media_id = str(item.get("id", "")).strip()
            media_ts = _parse_timestamp(item.get("timestamp"))
            caption_text = item.get("caption")
            game_type, day_number = parse_game_info(caption_text)
            caption_blank = not str(caption_text or "").strip()
            source = "recent_media"
            if (not game_type or not day_number) and media_ts:
                inferred = _infer_game_day_from_upload_logs(
                    media_ts,
                    prefer_caption_error=caption_blank,
                )
                if inferred:
                    game_type = game_type or inferred.get("game_type")
                    day_number = day_number or inferred.get("day_number")
                    source = "recent_media_upload_log_ts"
            if day_number and not game_type and media_ts:
                inferred = _infer_game_for_known_day(day_number, media_ts, allow_ambiguous=True)
                if inferred:
                    game_type = inferred.get("game_type")
                    source = "recent_media_known_day_ts"
            if game_type and not day_number and media_ts:
                inferred = _infer_day_for_known_game(game_type, media_ts, allow_ambiguous=True)
                if inferred:
                    day_number = inferred.get("day_number")
                    source = "recent_media_known_game_ts"
            if not media_id or not game_type or not day_number:
                continue

            previous = _MEDIA_GAME_MAP.get(media_id)
            if previous:
                try:
                    prev_day = int(previous.get("day_number"))
                except Exception:
                    prev_day = None
                if previous.get("game_type") == game_type and prev_day == int(day_number):
                    _MEDIA_GAME_MAP.move_to_end(media_id)
                    continue

            _MEDIA_GAME_MAP[media_id] = {
                "game_type": str(game_type),
                "day_number": int(day_number),
                "source": source,
                "updated_at": updated_at,
            }
            _MEDIA_GAME_MAP.move_to_end(media_id)
            mapped += 1
            changed = True

        while len(_MEDIA_GAME_MAP) > MEDIA_GAME_MAP_MAX_ENTRIES:
            _MEDIA_GAME_MAP.popitem(last=False)
            changed = True

        if changed:
            _save_media_game_map()
            print(f"Backfilled {mapped} media mappings from recent posts")
        return mapped


def _available_day_numbers():
    if WEBHOOK_USE_LOCAL_HISTORY:
        _load_local_history()
        day_numbers = list(_LOCAL_DAY_INDEX.keys())
        day_numbers.sort()
        return day_numbers
    days_dir = DATA_ROOT / "days"
    if not days_dir.exists():
        return []
    day_numbers = []
    for day_file in days_dir.glob("*.json"):
        try:
            day_numbers.append(int(day_file.stem))
        except Exception:
            continue
    day_numbers.sort()
    return day_numbers


_UPLOAD_FILE_RE = re.compile(r"^(.+?)_day_(\d+)\.mp4$", re.IGNORECASE)
_UPLOAD_LOG_RE = re.compile(r"upload_(\d{8})_\d{6}\.log$", re.IGNORECASE)
_LOG_TIME_RE = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\]")


def _upload_log_tzinfo():
    if ZoneInfo is not None:
        try:
            return ZoneInfo(UPLOAD_LOG_TIMEZONE)
        except Exception:
            pass
    try:
        return datetime.now().astimezone().tzinfo
    except Exception:
        return timezone.utc


def _parse_upload_filename(filename):
    match = _UPLOAD_FILE_RE.match(str(filename).strip())
    if not match:
        return None, None
    game_type = normalize_game_mode(match.group(1))
    if not game_type:
        return None, None
    try:
        day_number = int(match.group(2))
    except Exception:
        return None, None
    return game_type, day_number


def _build_upload_timeline():
    global _UPLOAD_TIMELINE
    if _UPLOAD_TIMELINE is not None:
        return _UPLOAD_TIMELINE

    timeline = []
    if not UPLOAD_LOG_FALLBACK_ON_MISS:
        _UPLOAD_TIMELINE = timeline
        return _UPLOAD_TIMELINE
    if not UPLOAD_LOG_DIR.exists():
        _UPLOAD_TIMELINE = timeline
        return _UPLOAD_TIMELINE

    log_files = sorted(UPLOAD_LOG_DIR.glob("upload_*.log"))
    if UPLOAD_LOG_MAX_FILES > 0:
        log_files = log_files[-UPLOAD_LOG_MAX_FILES:]

    tzinfo = _upload_log_tzinfo()
    for log_path in log_files:
        log_match = _UPLOAD_LOG_RE.match(log_path.name)
        if not log_match:
            continue
        try:
            base_day = datetime.strptime(log_match.group(1), "%Y%m%d").date()
        except Exception:
            continue

        current_upload = None
        previous_wall_time = None
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for line in lines:
            start_match = re.search(r"IG: Uploading ([^\s]+\.mp4)", line)
            if start_match:
                game_type, day_number = _parse_upload_filename(Path(start_match.group(1)).name)
                if game_type and day_number:
                    current_upload = {
                        "game_type": game_type,
                        "day_number": day_number,
                        "filename": start_match.group(1),
                        "caption_error": False,
                    }
                else:
                    current_upload = None
                continue

            if not current_upload:
                continue
            if "Error adding caption" in line:
                current_upload["caption_error"] = True
                continue
            if "COMPLETE: Upload successful!" not in line:
                continue

            tm = _LOG_TIME_RE.match(line)
            if not tm:
                continue
            hour = int(tm.group(1))
            minute = int(tm.group(2))
            second = int(tm.group(3))
            wall_dt = datetime.combine(base_day, datetime.min.time()).replace(
                hour=hour,
                minute=minute,
                second=second,
            )

            # Handle midnight rollover for long-running upload sessions.
            if previous_wall_time and wall_dt < (previous_wall_time - timedelta(hours=12)):
                wall_dt = wall_dt + timedelta(days=1)
            previous_wall_time = wall_dt

            local_dt = wall_dt.replace(tzinfo=tzinfo)
            timeline.append(
                {
                    "timestamp": local_dt.astimezone(timezone.utc),
                    "game_type": current_upload["game_type"],
                    "day_number": current_upload["day_number"],
                    "source_log": log_path.name,
                    "filename": current_upload["filename"],
                    "caption_error": bool(current_upload.get("caption_error")),
                }
            )
            current_upload = None

    timeline.sort(key=lambda item: item["timestamp"])
    _UPLOAD_TIMELINE = timeline
    return _UPLOAD_TIMELINE


def _infer_game_day_from_upload_logs(media_ts, prefer_caption_error=False):
    if not media_ts:
        return None
    timeline = _build_upload_timeline()
    if not timeline:
        return None
    if prefer_caption_error:
        flagged = [item for item in timeline if item.get("caption_error")]
        if flagged:
            timeline = flagged
    best = []
    for item in timeline:
        diff = abs((item["timestamp"] - media_ts).total_seconds())
        best.append((diff, item))
    best.sort(key=lambda x: x[0])
    max_allowed = max(0.0, UPLOAD_LOG_MATCH_MAX_MINUTES) * 60.0
    if best[0][0] > max_allowed:
        return None
    return best[0][1]


def _build_game_timeline():
    global _GAME_TIMELINE
    if _GAME_TIMELINE is not None:
        return _GAME_TIMELINE
    timeline = []
    for day in _available_day_numbers():
        summary = load_day_summary(day)
        if not summary:
            continue
        for game in summary.get("games", []):
            ts = _parse_timestamp(game.get("timestamp"))
            if not ts:
                continue
            game_type = game.get("game_type")
            if not game_type:
                continue
            timeline.append(
                {
                    "timestamp": ts,
                    "day_number": day,
                    "game_type": game_type,
                    "game_id": game.get("game_id"),
                }
            )
    timeline.sort(key=lambda item: item["timestamp"])
    _GAME_TIMELINE = timeline
    return _GAME_TIMELINE


def _pick_timestamp_candidate(candidates, media_ts, allow_ambiguous=False):
    if not candidates or not media_ts:
        return None
    best = []
    for item in candidates:
        diff = abs((item["timestamp"] - media_ts).total_seconds())
        best.append((diff, item))
    best.sort(key=lambda x: x[0])
    max_allowed = MEDIA_TS_MATCH_MAX_HOURS * 3600
    if best[0][0] > max_allowed:
        return None
    if (
        not allow_ambiguous
        and len(best) > 1
        and (best[1][0] - best[0][0]) < MEDIA_TS_AMBIGUITY_MIN_GAP_SECONDS
    ):
        # Too close to call confidently.
        return None
    return best[0][1]


def _infer_game_day_from_timestamp(media_ts, allow_ambiguous=False):
    timeline = _build_game_timeline()
    return _pick_timestamp_candidate(
        timeline,
        media_ts,
        allow_ambiguous=allow_ambiguous,
    )


def _infer_game_for_known_day(day_number, media_ts, allow_ambiguous=False):
    summary = load_day_summary(day_number)
    if not summary:
        return None
    candidates = []
    for game in summary.get("games", []):
        ts = _parse_timestamp(game.get("timestamp"))
        game_type = game.get("game_type")
        if not ts or not game_type:
            continue
        candidates.append(
            {
                "timestamp": ts,
                "day_number": int(day_number),
                "game_type": game_type,
                "game_id": game.get("game_id"),
            }
        )
    return _pick_timestamp_candidate(
        candidates,
        media_ts,
        allow_ambiguous=allow_ambiguous,
    )


def _infer_day_for_known_game(game_type, media_ts, allow_ambiguous=False):
    game_candidates = set(_smb_mode_candidates(game_type))
    if not game_candidates:
        game_candidates = {game_type}
    timeline = [
        item for item in _build_game_timeline()
        if item.get("game_type") in game_candidates
    ]
    return _pick_timestamp_candidate(
        timeline,
        media_ts,
        allow_ambiguous=allow_ambiguous,
    )


def _find_nearby_day_with_game(game_type, day_number, media_ts):
    if not game_type or not day_number:
        return None, None
    candidates = []
    for delta in range(1, max(1, NEARBY_DAY_FALLBACK_RADIUS) + 1):
        for sign in (-1, 1):
            candidate_day = int(day_number) + (delta * sign)
            if candidate_day <= 0:
                continue
            summary = load_day_summary(candidate_day)
            if not summary:
                continue
            entry = find_game_entry(summary, game_type)
            if not entry:
                continue
            ts = _parse_timestamp(entry.get("timestamp"))
            candidates.append(
                {
                    "timestamp": ts if ts else datetime(1970, 1, 1, tzinfo=timezone.utc),
                    "day_number": candidate_day,
                    "game_type": game_type,
                    "game_id": entry.get("game_id"),
                    "day_delta": abs(candidate_day - int(day_number)),
                }
            )
    if not candidates:
        return None, None
    if media_ts:
        picked = _pick_timestamp_candidate(candidates, media_ts)
        if picked:
            return picked["day_number"], picked["game_id"]
    picked = sorted(candidates, key=lambda item: item["day_delta"])[0]
    return picked["day_number"], picked["game_id"]


def load_game_results(game_id):
    if not game_id:
        return None
    if WEBHOOK_USE_LOCAL_HISTORY:
        _load_local_history()
        game = _LOCAL_GAME_INDEX.get(game_id)
        if isinstance(game, dict):
            return game
    return load_json_file(DATA_ROOT / "games" / f"{game_id}.json")


def get_user_placement(game_data, username):
    if not game_data or not username:
        return None
    target = username.lstrip("@").lower()
    for entry in game_data.get("results", []):
        entry_name = str(entry.get("username", "")).lower()
        if entry_name == target:
            return entry.get("placement")
    return None


def format_results_message(game_display, day_number, placement):
    template = _choose_variant(RESULTS_MESSAGE_TEMPLATES)
    return template.format(
        game_display=game_display,
        day_number=day_number,
        placement=placement,
        RESULTS_FOOTER=RESULTS_FOOTER,
    )


def format_not_following_message():
    template = _choose_variant(NOT_FOLLOWING_TEMPLATES)
    return template.format(RESULTS_FOOTER=RESULTS_FOOTER)


def _load_club_member_set():
    global _CLUB_MEMBER_SET
    if _CLUB_MEMBER_SET is not None:
        return _CLUB_MEMBER_SET
    try:
        club_path = BASE_DIR / "Followers" / "club_members_followers.json"
        data = load_json_file(club_path)
        if not isinstance(data, list):
            _CLUB_MEMBER_SET = set()
            return _CLUB_MEMBER_SET
        members = set()
        for entry in data:
            if isinstance(entry, dict):
                username = str(entry.get("username", "")).strip().lower()
                if username:
                    members.add(username)
        _CLUB_MEMBER_SET = members
        return _CLUB_MEMBER_SET
    except Exception as exc:
        print(f"Failed to load club members: {exc}")
        _CLUB_MEMBER_SET = set()
        return _CLUB_MEMBER_SET


def format_club_not_member_message():
    return _choose_variant(CLUB_NOT_MEMBER_TEMPLATES)


def format_results_not_ready_message():
    template = _choose_variant(RESULTS_NOT_READY_TEMPLATES)
    return template.format(RESULTS_FOOTER=RESULTS_FOOTER)

def format_facebook_future_games_message():
    return (
        FACEBOOK_RESULT_FUTURE_GAMES_REPLY_TEXT
        or "You've been added to the follower list and will be part of future games soon."
    )


def format_youtube_future_games_message():
    return (
        YOUTUBE_RESULT_FUTURE_GAMES_REPLY_TEXT
        or "You've been added to the follower list and will be part of future games soon."
    )


def format_discord_only_message():
    template = _choose_variant(DISCORD_ONLY_MESSAGE_TEMPLATES)
    return template.format(RESULTS_FOOTER=RESULTS_FOOTER)


def format_discord_username_not_found_message():
    template = _choose_variant(DISCORD_USERNAME_NOT_FOUND_TEMPLATES)
    return template.format(RESULTS_FOOTER=RESULTS_FOOTER)


def extract_discord_username(comment_text):
    if not comment_text:
        return None
    match = re.search(r"\bresult\s*[:+]\s*(@?[A-Za-z0-9_.-]+)", comment_text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lstrip("@").strip()


_DISCORD_FOLLOWER_MAP = None
_CLUB_MEMBER_SET = None
_FOLLOWER_USERNAME_SET = None
_FOLLOWER_USERNAME_MTIME = None
_DAY_SUMMARY_CACHE = {}
_GAME_TIMELINE = None
_UPLOAD_TIMELINE = None
_MEDIA_GAME_MAP = OrderedDict()
_MEDIA_GAME_MAP_LOADED = False
_LAST_MEDIA_BACKFILL_AT = 0.0
_MEDIA_BACKFILL_LOCK = threading.Lock()
_PROCESSED_COMMENT_IDS = OrderedDict()
_PROCESSED_COMMENT_IDS_LOADED = False
_PROCESSED_LOCK = threading.Lock()
_PROCESSING_COMMENT_KEYS = set()
_YOUTUBE_CLIENT = None
_YOUTUBE_CLIENT_LOCK = threading.Lock()
_YOUTUBE_POLLER_STARTED = False
_YOUTUBE_CHANNEL_ID_CACHE = ""
_YOUTUBE_LIBS = None
_YOUTUBE_LIBS_FAILED = False

_REPLY_QUEUE = queue.Queue(maxsize=REPLY_QUEUE_MAX)
_REPLY_WORKER_STARTED = False
_REPLY_BACKOFF_UNTIL = 0.0
_QUEUE_LOCK = threading.Lock()
_QUEUE_PENDING = OrderedDict()
_QUEUE_PENDING_BY_KEY = {}
_QUEUE_LOADED = False
_START_TIME = time.time()
_REPLY_STATS = {
    "enqueued": 0,
    "sent": 0,
    "failed": 0,
    "dropped": 0,
    "last_reply_at": None,
    "last_error_subcode": None,
    "last_block_at": None,
}


def _choose_variant(templates):
    if not templates:
        return ""
    return random.choice(list(templates))


def _invalidate_follower_username_cache():
    global _FOLLOWER_USERNAME_SET, _FOLLOWER_USERNAME_MTIME
    _FOLLOWER_USERNAME_SET = None
    _FOLLOWER_USERNAME_MTIME = None


def _load_follower_username_set():
    global _FOLLOWER_USERNAME_SET, _FOLLOWER_USERNAME_MTIME
    try:
        mtime = FOLLOWER_STORE_PATH.stat().st_mtime
    except Exception:
        if _FOLLOWER_USERNAME_SET is None:
            _FOLLOWER_USERNAME_SET = set()
        _FOLLOWER_USERNAME_MTIME = None
        return _FOLLOWER_USERNAME_SET

    if _FOLLOWER_USERNAME_SET is not None and _FOLLOWER_USERNAME_MTIME == mtime:
        return _FOLLOWER_USERNAME_SET

    usernames = set()
    payload = load_json_file(FOLLOWER_STORE_PATH)
    if isinstance(payload, list):
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            username = str(entry.get("username", "")).strip().lower()
            if username:
                usernames.add(username)
    _FOLLOWER_USERNAME_SET = usernames
    _FOLLOWER_USERNAME_MTIME = mtime
    return _FOLLOWER_USERNAME_SET


def _is_username_in_follower_store(username):
    normalized = str(username or "").strip().lower()
    if not normalized:
        return False
    return normalized in _load_follower_username_set()


def _ensure_log_dir():
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _contains_keyword_word(text, keywords):
    body = str(text or "")
    if not body:
        return False
    for keyword in (keywords or []):
        token = str(keyword or "").strip()
        if not token:
            continue
        pattern = rf"\b{re.escape(token)}\b"
        if re.search(pattern, body, re.IGNORECASE):
            return True
    return False


def _youtube_features_enabled():
    return bool(YOUTUBE_ENABLE_JOIN_CAPTURE or YOUTUBE_ENABLE_RESULT_REPLIES)


def _youtube_poller_enabled():
    return bool(_youtube_features_enabled() and YOUTUBE_COMMENT_POLL_ENABLED)


def _youtube_required_scopes():
    return ["https://www.googleapis.com/auth/youtube.force-ssl"]


def _import_youtube_client_libs():
    global _YOUTUBE_LIBS, _YOUTUBE_LIBS_FAILED
    if _YOUTUBE_LIBS is not None:
        return _YOUTUBE_LIBS
    if _YOUTUBE_LIBS_FAILED:
        return None
    try:
        import pickle
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        _YOUTUBE_LIBS = {
            "pickle": pickle,
            "build": build,
            "Request": Request,
            "InstalledAppFlow": InstalledAppFlow,
        }
        return _YOUTUBE_LIBS
    except Exception as exc:
        print(f"YouTube API libraries not available: {exc}")
        _YOUTUBE_LIBS_FAILED = True
        return None


def _load_pickled_credentials(path):
    libs = _import_youtube_client_libs()
    if libs is None:
        return None
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            return libs["pickle"].load(handle)
    except Exception as exc:
        print(f"Failed to load YouTube token from {path}: {exc}")
        return None


def _save_pickled_credentials(path, creds):
    libs = _import_youtube_client_libs()
    if libs is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            libs["pickle"].dump(creds, handle)
    except Exception as exc:
        print(f"Failed to save YouTube token to {path}: {exc}")


def _credentials_include_scopes(creds, required_scopes):
    if creds is None:
        return False
    scopes = getattr(creds, "scopes", None)
    if not scopes:
        # Older token formats may not expose scopes; allow runtime API checks.
        return True
    current = {str(scope).strip() for scope in scopes if str(scope).strip()}
    required = {str(scope).strip() for scope in required_scopes if str(scope).strip()}
    return required.issubset(current)


def _load_youtube_credentials(allow_interactive=False):
    libs = _import_youtube_client_libs()
    if libs is None:
        return None

    required_scopes = _youtube_required_scopes()
    token_candidates = []
    for candidate in (YOUTUBE_COMMENT_TOKEN_PATH, YOUTUBE_UPLOAD_TOKEN_PATH):
        if candidate and candidate not in token_candidates:
            token_candidates.append(candidate)

    creds = None
    source_path = None
    for candidate in token_candidates:
        candidate_creds = _load_pickled_credentials(candidate)
        if candidate_creds is None:
            continue
        if _credentials_include_scopes(candidate_creds, required_scopes):
            creds = candidate_creds
            source_path = candidate
            break
        if creds is None:
            creds = candidate_creds
            source_path = candidate

    if creds is not None and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        try:
            creds.refresh(libs["Request"]())
            if source_path:
                _save_pickled_credentials(source_path, creds)
        except Exception as exc:
            print(f"Failed to refresh YouTube credentials: {exc}")
            creds = None

    if creds is not None and not _credentials_include_scopes(creds, required_scopes):
        print(
            "YouTube token is missing required scope for comments/replies "
            f"({required_scopes})."
        )
        if not allow_interactive:
            return None
        creds = None

    if creds is None and allow_interactive:
        if not YOUTUBE_CLIENT_SECRET_PATH.exists():
            print(
                f"YouTube interactive auth unavailable: missing client secret "
                f"{YOUTUBE_CLIENT_SECRET_PATH}"
            )
            return None
        try:
            flow = libs["InstalledAppFlow"].from_client_secrets_file(
                str(YOUTUBE_CLIENT_SECRET_PATH),
                required_scopes,
            )
            creds = flow.run_local_server(port=0)
            _save_pickled_credentials(YOUTUBE_COMMENT_TOKEN_PATH, creds)
            print(f"YouTube comment token saved: {YOUTUBE_COMMENT_TOKEN_PATH}")
        except Exception as exc:
            print(f"YouTube interactive auth failed: {exc}")
            return None

    return creds


def _get_youtube_client(allow_interactive=False, force_refresh=False):
    global _YOUTUBE_CLIENT
    with _YOUTUBE_CLIENT_LOCK:
        if force_refresh:
            _YOUTUBE_CLIENT = None
        if _YOUTUBE_CLIENT is not None:
            return _YOUTUBE_CLIENT
        libs = _import_youtube_client_libs()
        if libs is None:
            return None
        creds = _load_youtube_credentials(allow_interactive=allow_interactive)
        if creds is None:
            return None
        try:
            _YOUTUBE_CLIENT = libs["build"](
                "youtube",
                "v3",
                credentials=creds,
                cache_discovery=False,
            )
        except Exception as exc:
            print(f"Failed to build YouTube client: {exc}")
            _YOUTUBE_CLIENT = None
        return _YOUTUBE_CLIENT


def _resolve_youtube_channel_id(youtube_client=None):
    global _YOUTUBE_CHANNEL_ID_CACHE
    configured = str(YOUTUBE_CHANNEL_ID or "").strip()
    if configured:
        return configured
    if _YOUTUBE_CHANNEL_ID_CACHE:
        return _YOUTUBE_CHANNEL_ID_CACHE
    youtube = youtube_client or _get_youtube_client(allow_interactive=False)
    if youtube is None:
        return ""
    try:
        response = youtube.channels().list(part="id,snippet", mine=True, maxResults=1).execute()
        items = response.get("items") if isinstance(response, dict) else []
        if not isinstance(items, list) or not items:
            print("YouTube channel lookup returned no channels for this token.")
            return ""
        channel_id = str(items[0].get("id") or "").strip()
        if channel_id:
            _YOUTUBE_CHANNEL_ID_CACHE = channel_id
        return channel_id
    except Exception as exc:
        print(f"YouTube channel lookup failed: {exc}")
        return ""


def _fetch_youtube_video_metadata(video_id):
    video_ref = str(video_id or "").strip()
    if not video_ref:
        return {}
    youtube = _get_youtube_client(allow_interactive=False)
    if youtube is None:
        return {}
    try:
        response = youtube.videos().list(part="snippet", id=video_ref, maxResults=1).execute()
        items = response.get("items") if isinstance(response, dict) else []
        if not isinstance(items, list) or not items:
            return {}
        snippet = items[0].get("snippet") if isinstance(items[0], dict) else {}
        if not isinstance(snippet, dict):
            return {}
        return {
            "id": video_ref,
            "title": str(snippet.get("title") or "").strip(),
            "description": str(snippet.get("description") or "").strip(),
            "published_at": snippet.get("publishedAt"),
            "channel_id": str(snippet.get("channelId") or "").strip(),
        }
    except Exception as exc:
        print(f"Failed to fetch YouTube video metadata {video_ref}: {exc}")
        return {}


def _youtube_capability_check():
    if not _youtube_features_enabled():
        print("YouTube comment features: disabled")
        return
    if not _youtube_poller_enabled():
        print("YouTube comment features enabled, but polling is disabled.")
        return
    youtube = _get_youtube_client(allow_interactive=YOUTUBE_ALLOW_INTERACTIVE_AUTH)
    if youtube is None:
        print("WARNING: YouTube comment features enabled but YouTube OAuth client is unavailable.")
        return
    channel_id = _resolve_youtube_channel_id(youtube)
    if not channel_id:
        print("WARNING: YouTube comment features enabled but no channel id could be resolved.")
        return
    try:
        youtube.commentThreads().list(
            part="snippet",
            allThreadsRelatedToChannelId=channel_id,
            order="time",
            maxResults=1,
            textFormat="plainText",
        ).execute()
        print(f"YouTube capability check OK for channel {channel_id}")
    except Exception as exc:
        print(f"WARNING: YouTube capability check failed: {exc}")


def _load_processed_comment_ids():
    global _PROCESSED_COMMENT_IDS_LOADED, _PROCESSED_COMMENT_IDS
    if _PROCESSED_COMMENT_IDS_LOADED:
        return
    _PROCESSED_COMMENT_IDS_LOADED = True
    data = load_json_file(PROCESSED_COMMENT_IDS_PATH)
    if isinstance(data, dict):
        ordered = sorted(
            data.items(),
            key=lambda kv: float(kv[1].get("ts", 0.0)) if isinstance(kv[1], dict) else 0.0,
        )
        for key, payload in ordered:
            if isinstance(payload, dict):
                _PROCESSED_COMMENT_IDS[str(key)] = payload
            else:
                _PROCESSED_COMMENT_IDS[str(key)] = {"ts": 0.0}
    elif isinstance(data, list):
        for key in data:
            _PROCESSED_COMMENT_IDS[str(key)] = {"ts": 0.0}
    while len(_PROCESSED_COMMENT_IDS) > max(1, PROCESSED_COMMENT_IDS_MAX):
        _PROCESSED_COMMENT_IDS.popitem(last=False)


def _save_processed_comment_ids():
    _ensure_log_dir()
    try:
        PROCESSED_COMMENT_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            key: payload
            for key, payload in _PROCESSED_COMMENT_IDS.items()
        }
        tmp_path = PROCESSED_COMMENT_IDS_PATH.with_suffix(PROCESSED_COMMENT_IDS_PATH.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(serializable, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, PROCESSED_COMMENT_IDS_PATH)
    except Exception as exc:
        print(f"Failed to save processed comment ids: {exc}")


def _is_comment_processed(key):
    if not key:
        return False
    with _PROCESSED_LOCK:
        _load_processed_comment_ids()
        return str(key) in _PROCESSED_COMMENT_IDS


def _claim_comment_processing(key):
    if not key:
        return False
    normalized = str(key)
    with _PROCESSED_LOCK:
        _load_processed_comment_ids()
        if normalized in _PROCESSED_COMMENT_IDS:
            return False
        if normalized in _PROCESSING_COMMENT_KEYS:
            return False
        _PROCESSING_COMMENT_KEYS.add(normalized)
        return True


def _release_comment_claim(key):
    if not key:
        return
    with _PROCESSED_LOCK:
        _PROCESSING_COMMENT_KEYS.discard(str(key))


def _mark_comment_processed(key, payload=None):
    if not key:
        return
    normalized = str(key)
    with _PROCESSED_LOCK:
        _load_processed_comment_ids()
        entry = {
            "ts": time.time(),
        }
        if isinstance(payload, dict):
            entry.update(payload)
        _PROCESSED_COMMENT_IDS[normalized] = entry
        _PROCESSED_COMMENT_IDS.move_to_end(normalized)
        _PROCESSING_COMMENT_KEYS.discard(normalized)
        while len(_PROCESSED_COMMENT_IDS) > max(1, PROCESSED_COMMENT_IDS_MAX):
            _PROCESSED_COMMENT_IDS.popitem(last=False)
        _save_processed_comment_ids()


def _append_queue_event(event_type, item_id, payload=None):
    _ensure_log_dir()
    event = {
        "ts": time.time(),
        "type": event_type,
        "id": item_id,
    }
    if payload:
        event.update(payload)
    try:
        with QUEUE_EVENTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"Failed to append queue event: {exc}")


def _save_queue_state():
    _ensure_log_dir()
    try:
        with QUEUE_STATE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(list(_QUEUE_PENDING.values()), handle, ensure_ascii=False, indent=2)
        with QUEUE_META_PATH.open("w", encoding="utf-8") as handle:
            json.dump({"ts": time.time(), "size": len(_QUEUE_PENDING)}, handle)
    except Exception as exc:
        print(f"Failed to save queue state: {exc}")


def _load_queue_state():
    if not QUEUE_STATE_PATH.exists():
        return []
    try:
        data = load_json_file(QUEUE_STATE_PATH)
        if isinstance(data, list):
            return data
    except Exception as exc:
        print(f"Failed to load queue state: {exc}")
    return []


def _load_queue_meta():
    if not QUEUE_META_PATH.exists():
        return None
    try:
        data = load_json_file(QUEUE_META_PATH)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def _queue_dedupe_key(comment_id, platform="instagram"):
    platform_name = str(platform or "instagram").strip().lower()
    return f"{platform_name}:{str(comment_id or '').strip()}"


def _pop_pending_queue_item(item_id):
    item = _QUEUE_PENDING.pop(item_id, None)
    if not item:
        return None
    dedupe_key = _queue_dedupe_key(item.get("comment_id"), item.get("platform"))
    if _QUEUE_PENDING_BY_KEY.get(dedupe_key) == item_id:
        _QUEUE_PENDING_BY_KEY.pop(dedupe_key, None)
    return item


def _queue_item_id(comment_id):
    suffix = random.randint(1000, 9999)
    return f"{comment_id}-{int(time.time() * 1000)}-{suffix}"


def _restore_queue_from_state():
    global _QUEUE_LOADED
    if _QUEUE_LOADED:
        return
    _QUEUE_LOADED = True
    with _QUEUE_LOCK:
        state_items = _load_queue_state()
        if state_items:
            dropped_duplicates = 0
            for item in state_items:
                item_id = item.get("id")
                if not item_id or item_id in _QUEUE_PENDING:
                    continue
                item["platform"] = str(item.get("platform") or "instagram").strip().lower()
                if not item.get("access_token"):
                    if item["platform"] == "facebook":
                        item["access_token"] = FACEBOOK_PAGE_ACCESS_TOKEN
                    elif item["platform"] == "youtube":
                        item["access_token"] = "youtube_oauth"
                    else:
                        item["access_token"] = INSTAGRAM_ACCESS_TOKEN_APP
                queue_key = _queue_dedupe_key(item.get("comment_id"), item.get("platform"))
                if _QUEUE_PENDING_BY_KEY.get(queue_key):
                    dropped_duplicates += 1
                    continue
                _QUEUE_PENDING[item_id] = item
                _QUEUE_PENDING_BY_KEY[queue_key] = item_id
                try:
                    _REPLY_QUEUE.put_nowait(item_id)
                except queue.Full:
                    print("Reply queue full while restoring - truncating persisted queue")
                    break
            restored = len(_QUEUE_PENDING)
            print(f"Restored {restored} queued replies from previous run")
            if dropped_duplicates:
                print(f"Removed {dropped_duplicates} duplicate queued replies during restore")
                _save_queue_state()
            if restored > REPLY_QUEUE_WARN_THRESHOLD:
                print(f"WARNING: restarting with {restored} queued replies pending")
        else:
            meta = _load_queue_meta()
            if meta and meta.get("size", 0) > REPLY_QUEUE_WARN_THRESHOLD:
                print(
                    f"WARNING: previous queue size {meta.get('size')} lost (no persisted queue state)"
                )


def _start_heartbeat():
    def _beat():
        start = time.time()
        pid = os.getpid()
        while True:
            uptime = int(time.time() - start)
            with _QUEUE_LOCK:
                pending = len(_QUEUE_PENDING)
            msg = f"{time.strftime('%Y-%m-%d %H:%M:%S')} pid={pid} uptime={uptime}s pending={pending}\n"
            try:
                _ensure_log_dir()
                with HEARTBEAT_LOG_PATH.open("a", encoding="utf-8") as handle:
                    handle.write(msg)
            except Exception:
                pass
            time.sleep(max(5.0, HEARTBEAT_INTERVAL_SECONDS))
    thread = threading.Thread(target=_beat, name="webhook-heartbeat", daemon=True)
    thread.start()


def _start_reply_worker_if_needed():
    global _REPLY_WORKER_STARTED
    if _REPLY_WORKER_STARTED:
        return
    _restore_queue_from_state()
    _REPLY_WORKER_STARTED = True
    worker = threading.Thread(target=_reply_worker, name="reply-worker", daemon=True)
    worker.start()
    print("Reply worker started")


def _load_discord_follower_map():
    global _DISCORD_FOLLOWER_MAP
    if _DISCORD_FOLLOWER_MAP is not None:
        return _DISCORD_FOLLOWER_MAP

    overrides = getattr(config, "FOLLOWER_IMPORT_FILE_BY_MODE", {}) or {}
    if isinstance(overrides, dict):
        import_path = (
            overrides.get("discord_signal")
            or overrides.get("plinko")
            or overrides.get("mingle")
            or overrides.get("lava_platform")
        )
    else:
        import_path = None

    if not import_path:
        import_path = getattr(config, "FOLLOWER_IMPORT_FILE", "") or "Followers/discord_followers.json"

    path = Path(import_path)
    if not path.is_absolute():
        path = BASE_DIR / path

    data = load_json_file(path)
    if not isinstance(data, list):
        _DISCORD_FOLLOWER_MAP = {}
        return _DISCORD_FOLLOWER_MAP

    mapping = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        discord_username = entry.get("discord_username")
        display_username = entry.get("username")
        if discord_username and display_username:
            key = str(discord_username).lower()
            if key not in mapping:
                mapping[key] = str(display_username)

    _DISCORD_FOLLOWER_MAP = mapping
    return _DISCORD_FOLLOWER_MAP


def _resolve_discord_display_name(discord_username):
    if not discord_username:
        return None
    mapping = _load_discord_follower_map()
    return mapping.get(str(discord_username).lower())


def _resolve_media_game_day(media_id):
    if not media_id:
        return None, None, None, "missing_media_id"

    cached = _lookup_media_mapping(media_id)
    if cached:
        return (
            cached.get("game_type"),
            cached.get("day_number"),
            None,
            f"cache:{cached.get('source', 'cache')}",
        )

    media_meta = fetch_media_metadata(media_id)
    caption = media_meta.get("caption")
    media_ts = _parse_timestamp(media_meta.get("timestamp"))
    game_type, day_number = parse_game_info(caption)
    caption_blank = not str(caption or "").strip()
    source = "unresolved"

    if game_type and day_number:
        _remember_media_mapping(media_id, game_type, day_number, "caption")
        return game_type, day_number, media_meta, "caption"

    if (not game_type or not day_number) and media_ts:
        inferred = _infer_game_day_from_upload_logs(
            media_ts,
            prefer_caption_error=caption_blank,
        )
        if inferred:
            game_type = game_type or inferred.get("game_type")
            day_number = day_number or inferred.get("day_number")
            source = "upload_log_ts"

    if day_number and not game_type:
        inferred = _infer_game_for_known_day(day_number, media_ts)
        if inferred:
            game_type = inferred.get("game_type")
            source = "known_day_ts"

    if game_type and not day_number:
        inferred = _infer_day_for_known_game(game_type, media_ts)
        if inferred:
            day_number = inferred.get("day_number")
            source = "known_game_ts"

    if (not game_type or not day_number) and media_ts:
        inferred = _infer_game_day_from_timestamp(media_ts)
        if inferred:
            game_type = game_type or inferred.get("game_type")
            day_number = day_number or inferred.get("day_number")
            source = "timestamp"

    # Last-resort fallback: when uploads are close in time, strict ambiguity
    # checks can reject valid matches; use nearest timestamp as a fallback.
    if (not game_type or not day_number) and media_ts:
        inferred = _infer_game_day_from_timestamp(media_ts, allow_ambiguous=True)
        if inferred:
            game_type = game_type or inferred.get("game_type")
            day_number = day_number or inferred.get("day_number")
            source = "timestamp_relaxed"

    if game_type and day_number:
        _remember_media_mapping(media_id, game_type, day_number, source)
        return game_type, day_number, media_meta, source

    return game_type, day_number, media_meta, "unresolved"


def _extract_caption_like_text(payload):
    if not isinstance(payload, dict):
        return ""
    for key in ("message", "description", "caption", "title"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def _remember_facebook_mapping(video_id, post_id, game_type, day_number, source, extra=None):
    if not game_type or not day_number:
        return
    if remember_facebook_media_mapping is None:
        return
    try:
        remember_facebook_media_mapping(
            FACEBOOK_MEDIA_GAME_MAP_PATH,
            video_id=str(video_id or "").strip() or None,
            post_id=str(post_id or "").strip() or None,
            game_type=str(game_type),
            day_number=int(day_number),
            source=str(source or "facebook"),
            extra=extra or {},
        )
    except Exception as exc:
        print(f"Failed to save FB media mapping: {exc}")


def _remember_youtube_mapping(video_id, game_type, day_number, source, extra=None):
    if not game_type or not day_number:
        return
    if remember_youtube_media_mapping is None:
        return
    try:
        remember_youtube_media_mapping(
            YOUTUBE_MEDIA_GAME_MAP_PATH,
            video_id=str(video_id or "").strip(),
            game_type=str(game_type),
            day_number=int(day_number),
            source=str(source or "youtube"),
            extra=extra or {},
        )
    except Exception as exc:
        print(f"Failed to save YouTube media mapping: {exc}")


def _resolve_youtube_game_day(comment_data):
    video_id = str(comment_data.get("video_id") or "").strip()
    comment_ts = _parse_timestamp(comment_data.get("published_at"))
    if not video_id:
        return None, None, "youtube_missing_video_id", comment_ts

    mapped = None
    if lookup_youtube_media_mapping is not None:
        mapped = lookup_youtube_media_mapping(
            YOUTUBE_MEDIA_GAME_MAP_PATH,
            video_id=video_id,
        )
    if mapped:
        return (
            mapped.get("game_type"),
            mapped.get("day_number"),
            "youtube_map",
            comment_ts,
        )

    video_meta = _fetch_youtube_video_metadata(video_id)
    title = str(video_meta.get("title") or "").strip()
    description = str(video_meta.get("description") or "").strip()
    media_ts = _parse_timestamp(video_meta.get("published_at")) or comment_ts

    game_type, day_number = parse_game_info(description or title)
    source = "youtube_description"

    if not game_type:
        game_type = _extract_game_mode_from_youtube_title(title)
        if game_type:
            source = "youtube_title"

    if not day_number:
        day_number = _extract_day_number_from_text(title) or _extract_day_number_from_text(description)

    if day_number and not game_type and media_ts:
        inferred = _infer_game_for_known_day(day_number, media_ts, allow_ambiguous=True)
        if inferred:
            game_type = inferred.get("game_type")
            source = "youtube_known_day_ts"

    if game_type and not day_number and media_ts:
        inferred = _infer_day_for_known_game(game_type, media_ts, allow_ambiguous=True)
        if inferred:
            day_number = inferred.get("day_number")
            source = "youtube_known_game_ts"

    if (not game_type or not day_number) and media_ts:
        inferred = _infer_game_day_from_upload_logs(media_ts)
        if inferred:
            game_type = game_type or inferred.get("game_type")
            day_number = day_number or inferred.get("day_number")
            source = "youtube_upload_log_ts"

    if (not game_type or not day_number) and media_ts:
        inferred = _infer_game_day_from_timestamp(media_ts, allow_ambiguous=True)
        if inferred:
            game_type = game_type or inferred.get("game_type")
            day_number = day_number or inferred.get("day_number")
            source = "youtube_timestamp"

    if game_type and day_number:
        _remember_youtube_mapping(
            video_id=video_id,
            game_type=game_type,
            day_number=day_number,
            source=source,
            extra={
                "title": title[:180],
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
            },
        )
        return game_type, int(day_number), source, media_ts

    return None, None, "youtube_unresolved", media_ts


def _resolve_facebook_game_day(comment_data):
    post_id = str(comment_data.get("post_id") or "").strip()
    parent_id = str(comment_data.get("parent_id") or "").strip()
    created_time = comment_data.get("created_time")
    media_ts = _parse_timestamp(created_time)

    mapped = None
    if lookup_facebook_media_mapping is not None:
        mapped = lookup_facebook_media_mapping(FACEBOOK_MEDIA_GAME_MAP_PATH, post_id=post_id)
        if not mapped and parent_id:
            mapped = lookup_facebook_media_mapping(FACEBOOK_MEDIA_GAME_MAP_PATH, post_id=parent_id)

    if mapped:
        return (
            mapped.get("game_type"),
            mapped.get("day_number"),
            "facebook_map",
            None,
        )

    resolved_post_id = post_id or parent_id
    post_meta = fetch_facebook_object_metadata(resolved_post_id) if resolved_post_id else {}
    caption_text = _extract_caption_like_text(post_meta)
    game_type, day_number = parse_game_info(caption_text)
    source = "facebook_post_meta"

    attachment_video_id = ""
    attachments = post_meta.get("attachments")
    if isinstance(attachments, dict):
        attachment_data = attachments.get("data")
        if isinstance(attachment_data, list):
            for item in attachment_data:
                if not isinstance(item, dict):
                    continue
                target = item.get("target")
                if isinstance(target, dict):
                    attachment_video_id = str(target.get("id") or "").strip()
                    if attachment_video_id:
                        break
    if attachment_video_id:
        mapped_video = None
        if lookup_facebook_media_mapping is not None:
            mapped_video = lookup_facebook_media_mapping(
                FACEBOOK_MEDIA_GAME_MAP_PATH,
                video_id=attachment_video_id,
                post_id=resolved_post_id,
            )
        if mapped_video:
            return (
                mapped_video.get("game_type"),
                mapped_video.get("day_number"),
                "facebook_map_video",
                media_ts,
            )
        video_meta = fetch_facebook_object_metadata(attachment_video_id)
    else:
        video_meta = {}
    if not game_type or not day_number:
        video_caption_text = _extract_caption_like_text(video_meta)
        if video_caption_text:
            source = "facebook_video_meta"
            parsed_game, parsed_day = parse_game_info(video_caption_text)
            if parsed_game:
                game_type = parsed_game
            if parsed_day:
                day_number = parsed_day
            if not caption_text:
                caption_text = video_caption_text

    if not media_ts:
        media_ts = _parse_timestamp(post_meta.get("created_time"))
    if not media_ts:
        media_ts = _parse_timestamp(video_meta.get("created_time"))

    if day_number and not game_type and media_ts:
        inferred = _infer_game_for_known_day(day_number, media_ts, allow_ambiguous=True)
        if inferred:
            game_type = inferred.get("game_type")
            source = "facebook_known_day_ts"

    if game_type and not day_number and media_ts:
        inferred = _infer_day_for_known_game(game_type, media_ts, allow_ambiguous=True)
        if inferred:
            day_number = inferred.get("day_number")
            source = "facebook_known_game_ts"

    if (not game_type or not day_number) and media_ts:
        inferred = _infer_game_day_from_upload_logs(media_ts)
        if inferred:
            game_type = game_type or inferred.get("game_type")
            day_number = day_number or inferred.get("day_number")
            source = "facebook_upload_log_ts"

    if (not game_type or not day_number) and media_ts:
        inferred = _infer_game_day_from_timestamp(media_ts, allow_ambiguous=True)
        if inferred:
            game_type = game_type or inferred.get("game_type")
            day_number = day_number or inferred.get("day_number")
            source = "facebook_timestamp"

    if game_type and day_number:
        _remember_facebook_mapping(
            video_id=attachment_video_id,
            post_id=resolved_post_id,
            game_type=game_type,
            day_number=day_number,
            source=source,
            extra={
                "caption_excerpt": caption_text[:240] if caption_text else "",
                "permalink": str(post_meta.get("permalink_url") or video_meta.get("permalink_url") or "").strip(),
            },
        )
        return game_type, int(day_number), source, media_ts

    return None, None, "facebook_unresolved", media_ts


def build_youtube_results_message(comment_data, comment_text=None):
    comment_id = str(comment_data.get("id") or "").strip()
    from_data = comment_data.get("from") if isinstance(comment_data.get("from"), dict) else {}
    commenter_name = str(from_data.get("name") or "YouTube User").strip()
    commenter_id = str(from_data.get("id") or "").strip()

    game_type, day_number, mapping_source, media_ts = _resolve_youtube_game_day(comment_data)
    if not game_type or not day_number:
        print(f"YouTube RESULT unresolved game/day for comment {comment_id} (source={mapping_source})")
        return format_results_not_ready_message()

    day_summary = load_day_summary(day_number)
    if not day_summary:
        nearby_day, _ = _find_nearby_day_with_game(game_type, day_number, media_ts)
        if nearby_day:
            day_number = nearby_day
            day_summary = load_day_summary(day_number)
    if not day_summary:
        print(f"YouTube RESULT no day summary for day {day_number} game {game_type}")
        return format_results_not_ready_message()

    game_entry = find_game_entry(day_summary, game_type)
    if not game_entry:
        nearby_day, nearby_game_id = _find_nearby_day_with_game(game_type, day_number, media_ts)
        if nearby_day and nearby_game_id:
            day_number = nearby_day
            day_summary = load_day_summary(day_number)
            game_entry = day_summary and next(
                (g for g in day_summary.get("games", []) if g.get("game_id") == nearby_game_id),
                None,
            )
    if not game_entry:
        print(f"YouTube RESULT no game entry for day {day_number} game {game_type}")
        return format_results_not_ready_message()

    game_data = load_game_results(game_entry.get("game_id"))
    if not game_data:
        return format_results_not_ready_message()

    candidates = []
    mapped_username = None
    if lookup_username_by_youtube_channel_id is not None:
        mapped_username = lookup_username_by_youtube_channel_id(
            FOLLOWER_STORE_PATH,
            commenter_id,
        )
    if mapped_username:
        candidates.append(mapped_username)
    if commenter_name:
        candidates.append(commenter_name)

    placement = None
    chosen_username = None
    for candidate in candidates:
        placement = get_user_placement(game_data, candidate)
        if placement is not None:
            chosen_username = candidate
            break

    if placement is None:
        print(
            f"YouTube RESULT user not found for comment {comment_id}: "
            f"name='{commenter_name}' mapped='{mapped_username}'"
        )
        if _is_smb_mode(game_type) or game_type in CLUB_ONLY_GAMES:
            members = _load_club_member_set()
            if commenter_name and commenter_name.lower() not in members:
                return format_club_not_member_message()
        follower_in_list = bool(mapped_username)
        if not follower_in_list and commenter_name:
            follower_in_list = _is_username_in_follower_store(commenter_name)
        if follower_in_list:
            return format_youtube_future_games_message()
        return format_not_following_message()

    day_value = game_data.get("day_number", day_number)
    game_display = _smb_display_name(game_type) or GAME_DISPLAY_NAMES.get(
        game_type,
        game_type.replace("_", " ").title(),
    )
    print(
        f"YouTube RESULT reply for comment {comment_id}: "
        f"user='{chosen_username}' placement={placement} day={day_value} game={game_type}"
    )
    return format_results_message(game_display, day_value, placement)


def build_facebook_results_message(comment_data, comment_text=None):
    comment_id = str(comment_data.get("id") or "").strip()
    from_data = comment_data.get("from") if isinstance(comment_data.get("from"), dict) else {}
    commenter_name = str(from_data.get("name") or "Facebook User").strip()
    commenter_id = str(from_data.get("id") or "").strip()

    game_type, day_number, mapping_source, media_ts = _resolve_facebook_game_day(comment_data)
    if not game_type or not day_number:
        print(f"FB RESULT unresolved game/day for comment {comment_id} (source={mapping_source})")
        return format_results_not_ready_message()

    day_summary = load_day_summary(day_number)
    if not day_summary:
        nearby_day, _ = _find_nearby_day_with_game(game_type, day_number, media_ts)
        if nearby_day:
            day_number = nearby_day
            day_summary = load_day_summary(day_number)
    if not day_summary:
        print(f"FB RESULT no day summary for day {day_number} game {game_type}")
        return format_results_not_ready_message()

    game_entry = find_game_entry(day_summary, game_type)
    if not game_entry:
        nearby_day, nearby_game_id = _find_nearby_day_with_game(game_type, day_number, media_ts)
        if nearby_day and nearby_game_id:
            day_number = nearby_day
            day_summary = load_day_summary(day_number)
            game_entry = day_summary and next(
                (g for g in day_summary.get("games", []) if g.get("game_id") == nearby_game_id),
                None,
            )
    if not game_entry:
        print(f"FB RESULT no game entry for day {day_number} game {game_type}")
        return format_results_not_ready_message()

    game_data = load_game_results(game_entry.get("game_id"))
    if not game_data:
        return format_results_not_ready_message()

    candidates = []
    mapped_username = None
    if lookup_username_by_facebook_id is not None:
        mapped_username = lookup_username_by_facebook_id(FOLLOWER_STORE_PATH, commenter_id)
    if mapped_username:
        candidates.append(mapped_username)
    if commenter_name:
        candidates.append(commenter_name)

    placement = None
    chosen_username = None
    for candidate in candidates:
        placement = get_user_placement(game_data, candidate)
        if placement is not None:
            chosen_username = candidate
            break

    if placement is None:
        print(
            f"FB RESULT user not found for comment {comment_id}: "
            f"name='{commenter_name}' mapped='{mapped_username}'"
        )
        if _is_smb_mode(game_type) or game_type in CLUB_ONLY_GAMES:
            members = _load_club_member_set()
            if commenter_name and commenter_name.lower() not in members:
                return format_club_not_member_message()
        follower_in_list = bool(mapped_username)
        if not follower_in_list and commenter_name:
            follower_in_list = _is_username_in_follower_store(commenter_name)
        if follower_in_list:
            return format_facebook_future_games_message()
        return format_not_following_message()

    day_value = game_data.get("day_number", day_number)
    game_display = _smb_display_name(game_type) or GAME_DISPLAY_NAMES.get(
        game_type,
        game_type.replace("_", " ").title(),
    )

    print(
        f"FB RESULT reply for comment {comment_id}: "
        f"user='{chosen_username}' placement={placement} day={day_value} game={game_type}"
    )
    return format_results_message(game_display, day_value, placement)


def build_results_message(comment_data, comment_text=None):
    comment_id = comment_data.get("id")
    media_id = comment_data.get('media', {}).get('id')
    commenter_username = comment_data.get('from', {}).get('username')
    mention_prefix = f"@{commenter_username} " if commenter_username else ""

    game_type, day_number, media_meta, mapping_source = _resolve_media_game_day(media_id)

    if not game_type or not day_number:
        print(
            f"Missing game/day mapping for comment {comment_id} media {media_id} "
            f"(source={mapping_source})"
        )
        return format_results_not_ready_message()

    if _is_smb_mode(game_type):
        try:
            offset = int(getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71))
        except Exception:
            offset = 71
        if _should_apply_day_offset(mapping_source, day_number, offset):
            day_number = int(day_number) + offset
        else:
            day_number = int(day_number)
    elif _is_jetpack_mode(game_type):
        try:
            offset = int(
                getattr(
                    config,
                    "JETPACK_FOLLOWERS_DAY_OFFSET",
                    getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71),
                )
            )
        except Exception:
            offset = int(getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71))
        if _should_apply_day_offset(mapping_source, day_number, offset):
            day_number = int(day_number) + offset
        else:
            day_number = int(day_number)
    elif _is_crossy_mode(game_type):
        try:
            offset = int(
                getattr(
                    config,
                    "CROSSY_FOLLOWERS_DAY_OFFSET",
                    getattr(
                        config,
                        "JETPACK_FOLLOWERS_DAY_OFFSET",
                        getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71),
                    ),
                )
            )
        except Exception:
            offset = int(
                getattr(
                    config,
                    "JETPACK_FOLLOWERS_DAY_OFFSET",
                    getattr(config, "SUPER_FOLLOWER_BROS_DAY_OFFSET", 71),
                )
            )
        if _should_apply_day_offset(mapping_source, day_number, offset):
            day_number = int(day_number) + offset
        else:
            day_number = int(day_number)

    day_summary = load_day_summary(day_number)
    if not day_summary:
        media_ts = _parse_timestamp((media_meta or {}).get("timestamp"))
        nearby_day, _ = _find_nearby_day_with_game(game_type, day_number, media_ts)
        if nearby_day:
            print(f"No day summary for day {day_number}; using nearest day {nearby_day}")
            day_number = nearby_day
            day_summary = load_day_summary(day_number)
    if not day_summary:
        print(f"No day summary found for day {day_number} (media {media_id})")
        return format_results_not_ready_message()

    game_entry = find_game_entry(day_summary, game_type)
    if not game_entry:
        media_ts = _parse_timestamp((media_meta or {}).get("timestamp"))
        nearby_day, nearby_game_id = _find_nearby_day_with_game(game_type, day_number, media_ts)
        if nearby_day and nearby_game_id:
            print(
                f"No game entry for day {day_number} game {game_type}; "
                f"using day {nearby_day}"
            )
            day_number = nearby_day
            day_summary = load_day_summary(day_number)
            game_entry = find_game_entry(day_summary, game_type)
    if not game_entry:
        print(f"No game entry found for day {day_number} and game {game_type} (media {media_id})")
        return format_results_not_ready_message()

    game_data = load_game_results(game_entry.get("game_id"))
    if not game_data or not game_data.get("results"):
        print(f"No results found for game {game_entry.get('game_id')}")
        return format_results_not_ready_message()

    lookup_username = commenter_username
    candidates = []
    if game_type in DISCORD_ONLY_GAMES:
        lookup_username = extract_discord_username(comment_text or "")
        if not lookup_username:
            return mention_prefix + format_discord_only_message()
        candidates.append(lookup_username)
        mapped_username = _resolve_discord_display_name(lookup_username)
        if mapped_username and mapped_username.lower() != lookup_username.lower():
            candidates.append(mapped_username)
    else:
        candidates.append(lookup_username)

    placement = None
    for candidate in candidates:
        placement = get_user_placement(game_data, candidate)
        if placement is not None:
            lookup_username = candidate
            break
    if placement is None:
        print(f"User @{lookup_username} not found in results")
        if game_type in DISCORD_ONLY_GAMES:
            return format_discord_username_not_found_message()
        if _is_smb_mode(game_type) or game_type in CLUB_ONLY_GAMES:
            members = _load_club_member_set()
            if commenter_username and commenter_username.lower() not in members:
                return mention_prefix + format_club_not_member_message()
        return mention_prefix + format_not_following_message()

    day_value = game_data.get("day_number", day_number)
    game_display = _smb_display_name(game_type) or GAME_DISPLAY_NAMES.get(
        game_type,
        game_type.replace("_", " ").title(),
    )

    return mention_prefix + format_results_message(game_display, day_value, placement)


# ============== GRAPH API FUNCTIONS ==============


def fetch_facebook_object_metadata(object_id):
    if FACEBOOK_PAGE_ACCESS_TOKEN in {"", "YOUR_ACCESS_TOKEN_HERE"}:
        return {}
    object_ref = str(object_id or "").strip()
    if not object_ref:
        return {}

    version = str(FACEBOOK_GRAPH_API_VERSION or "v18.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{version}/{object_ref}"
    params = {
        "fields": (
            "id,message,description,created_time,permalink_url,post_id,parent_id,"
            "attachments{target{id},media_type,url,unshimmed_url}"
        ),
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {}
        print(f"Failed to fetch Facebook object {object_ref}: {response.status_code} - {response.text[:400]}")
    except Exception as exc:
        print(f"Error fetching Facebook object {object_ref}: {exc}")
    return {}


def fetch_facebook_comment_text(comment_id):
    payload = fetch_facebook_object_metadata(comment_id)
    message = str(payload.get("message") or "").strip()
    if message:
        return message
    return None

def fetch_comment_text(comment_id):
    if INSTAGRAM_ACCESS_TOKEN_APP == "YOUR_ACCESS_TOKEN_HERE":
        print("Access token not configured - cannot fetch comment text")
        return None
    if not comment_id:
        return None

    url = f"https://graph.facebook.com/v18.0/{comment_id}"
    params = {
        "fields": "text",
        "access_token": INSTAGRAM_ACCESS_TOKEN_APP,
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json().get("text")
        print(f"Failed to fetch comment text: {response.status_code} - {response.text}")
    except Exception as exc:
        print(f"Error fetching comment text: {exc}")

    return None


def fetch_media_metadata(media_id):
    if INSTAGRAM_ACCESS_TOKEN_APP == "YOUR_ACCESS_TOKEN_HERE":
        print("Access token not configured - cannot fetch media metadata")
        return {}
    if not media_id:
        return {}

    url = f"https://graph.facebook.com/v18.0/{media_id}"
    params = {
        "fields": "caption,media_product_type,timestamp,permalink",
        "access_token": INSTAGRAM_ACCESS_TOKEN_APP,
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {}
        print(f"Failed to fetch media caption: {response.status_code} - {response.text}")
    except Exception as exc:
        print(f"Error fetching media caption: {exc}")

    return {}


def fetch_media_caption(media_id):
    payload = fetch_media_metadata(media_id)
    return payload.get("caption")


def enqueue_reply(comment_id, message, platform="instagram", access_token=None):
    """Queue a reply to be sent at a steady rate."""
    platform_name = str(platform or "instagram").strip().lower()
    token_value = access_token
    if not token_value:
        if platform_name == "facebook":
            token_value = FACEBOOK_PAGE_ACCESS_TOKEN
        elif platform_name == "youtube":
            token_value = "youtube_oauth"
        else:
            token_value = INSTAGRAM_ACCESS_TOKEN_APP

    if platform_name != "youtube" and token_value in {"", "YOUR_ACCESS_TOKEN_HERE"}:
        print(f"Access token not configured for {platform_name} - reply not queued (test mode)")
        return False
    if platform_name == "youtube" and _get_youtube_client(allow_interactive=False) is None:
        print("YouTube OAuth is not configured - reply not queued")
        return False
    if not comment_id:
        print("Missing comment id - reply skipped")
        return False

    _start_reply_worker_if_needed()

    item_id = _queue_item_id(comment_id)
    item = {
        "id": item_id,
        "comment_id": comment_id,
        "message": message,
        "retries_left": REPLY_MAX_RETRIES,
        "platform": platform_name,
        "access_token": token_value,
    }

    with _QUEUE_LOCK:
        queue_key = _queue_dedupe_key(comment_id, platform_name)
        existing_item_id = _QUEUE_PENDING_BY_KEY.get(queue_key)
        if existing_item_id and existing_item_id in _QUEUE_PENDING:
            print(f"Reply already queued for {platform_name} comment {comment_id} - skipping duplicate enqueue")
            return True
        if existing_item_id and existing_item_id not in _QUEUE_PENDING:
            _QUEUE_PENDING_BY_KEY.pop(queue_key, None)
        if len(_QUEUE_PENDING) >= REPLY_QUEUE_MAX:
            print("Reply queue full - reply skipped")
            _REPLY_STATS["dropped"] += 1
            return False
        _QUEUE_PENDING[item_id] = item
        _QUEUE_PENDING_BY_KEY[queue_key] = item_id
        _append_queue_event("enqueue", item_id, {
            "comment_id": comment_id,
            "platform": platform_name,
            "retries_left": REPLY_MAX_RETRIES,
        })
        _save_queue_state()

    try:
        _REPLY_QUEUE.put_nowait(item_id)
        _REPLY_STATS["enqueued"] += 1
        return True
    except queue.Full:
        print("Reply queue full - reply skipped")
        _REPLY_STATS["dropped"] += 1
        with _QUEUE_LOCK:
            _pop_pending_queue_item(item_id)
            _append_queue_event("dropped", item_id, {"reason": "queue_full"})
            _save_queue_state()
        return False


def _post_youtube_reply(comment_id, message):
    youtube = _get_youtube_client(allow_interactive=False)
    if youtube is None:
        print("YouTube reply skipped: OAuth client unavailable")
        return False, None
    try:
        youtube.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": str(comment_id or "").strip(),
                    "textOriginal": str(message or ""),
                }
            },
        ).execute()
        return True, None
    except Exception as exc:
        print(f"YouTube reply request failed: {exc}")
        return False, None


def _post_reply(comment_id, message, platform="instagram", access_token=None):
    """Post a reply via platform API and return (success, error_subcode)."""
    platform_name = str(platform or "instagram").strip().lower()
    if platform_name == "youtube":
        success, subcode = _post_youtube_reply(comment_id, message)
        if success:
            print(f"Reply posted successfully for youtube comment {comment_id}")
            _REPLY_STATS["sent"] += 1
            _REPLY_STATS["last_reply_at"] = time.time()
            return True, None
        _REPLY_STATS["failed"] += 1
        return False, subcode

    version = str(
        FACEBOOK_GRAPH_API_VERSION if platform_name == "facebook" else "v18.0"
    ).strip().lstrip("/")
    if platform_name == "facebook":
        url = f"https://graph.facebook.com/{version}/{comment_id}/comments"
    else:
        url = f"https://graph.facebook.com/{version}/{comment_id}/replies"

    token_value = access_token
    if not token_value:
        token_value = FACEBOOK_PAGE_ACCESS_TOKEN if platform_name == "facebook" else INSTAGRAM_ACCESS_TOKEN_APP

    payload = {
        "message": message,
        "access_token": token_value,
    }

    try:
        response = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            print(f"Reply posted successfully for {platform_name} comment {comment_id}")
            _REPLY_STATS["sent"] += 1
            _REPLY_STATS["last_reply_at"] = time.time()
            return True, None
        print(f"Failed to post reply: {response.status_code} - {response.text}")
        try:
            error_payload = response.json().get("error", {})
            subcode = error_payload.get("error_subcode")
            _REPLY_STATS["failed"] += 1
            _REPLY_STATS["last_error_subcode"] = subcode
            return False, subcode
        except Exception:
            _REPLY_STATS["failed"] += 1
            return False, None
    except Exception as exc:
        print(f"Error posting reply: {exc}")
        return False, None


def _reply_worker():
    """Send queued replies at a steady rate with short backoff on IG blocks."""
    while True:
        item_id = _REPLY_QUEUE.get()
        with _QUEUE_LOCK:
            item = _QUEUE_PENDING.get(item_id)
        if not item:
            continue
        comment_id = item.get("comment_id")
        message = item.get("message")
        retries_left = item.get("retries_left", 0)
        platform = item.get("platform", "instagram")
        access_token = item.get("access_token")

        delay = random.uniform(REPLY_RATE_MIN_SECONDS, REPLY_RATE_MAX_SECONDS)
        if delay > 0:
            print(f"Waiting {delay:.1f}s before replying...")
            time.sleep(delay)

        success, subcode = _post_reply(comment_id, message, platform=platform, access_token=access_token)
        if success:
            with _QUEUE_LOCK:
                _pop_pending_queue_item(item_id)
                _append_queue_event("sent", item_id, {"comment_id": comment_id, "platform": platform})
                _save_queue_state()
            continue

        if not success and subcode == IG_REPLY_BLOCK_SUBCODE:
            if retries_left > 0:
                backoff = random.uniform(REPLY_BACKOFF_MIN_SECONDS, REPLY_BACKOFF_MAX_SECONDS)
                print(f"Reply blocked (1772107). Backing off {backoff:.1f}s and retrying later...")
                _REPLY_STATS["last_block_at"] = time.time()
                global _REPLY_BACKOFF_UNTIL
                _REPLY_BACKOFF_UNTIL = time.time() + backoff
                time.sleep(backoff)
                with _QUEUE_LOCK:
                    item["retries_left"] = retries_left - 1
                    _QUEUE_PENDING[item_id] = item
                    _append_queue_event("requeue", item_id, {"retries_left": retries_left - 1})
                    _save_queue_state()
                try:
                    _REPLY_QUEUE.put_nowait(item_id)
                except queue.Full:
                    print("Reply queue full after backoff - retry dropped")
                    _REPLY_STATS["dropped"] += 1
                    with _QUEUE_LOCK:
                        _pop_pending_queue_item(item_id)
                        _append_queue_event("dropped", item_id, {"reason": "queue_full_backoff", "platform": platform})
                        _save_queue_state()
            else:
                print("Reply blocked (1772107) and no retries left - dropping reply")
                _REPLY_STATS["dropped"] += 1
                with _QUEUE_LOCK:
                    _pop_pending_queue_item(item_id)
                    _append_queue_event("dropped", item_id, {"reason": "reply_blocked", "platform": platform})
                    _save_queue_state()
        else:
            with _QUEUE_LOCK:
                _pop_pending_queue_item(item_id)
                _append_queue_event("failed", item_id, {"reason": "reply_failed", "subcode": subcode, "platform": platform})
                _save_queue_state()


def _facebook_features_enabled():
    return bool(FACEBOOK_ENABLE_JOIN_CAPTURE or FACEBOOK_ENABLE_RESULT_REPLIES)


def _facebook_capability_check():
    if not _facebook_features_enabled():
        print("Facebook webhook features: disabled")
        return

    if not FACEBOOK_PAGE_ID:
        print("WARNING: Facebook webhook features enabled but FACEBOOK_PAGE_ID is missing.")
        return
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        print("WARNING: Facebook webhook features enabled but FACEBOOK_PAGE_ACCESS_TOKEN is missing.")
        return

    version = str(FACEBOOK_GRAPH_API_VERSION or "v18.0").strip().lstrip("/")
    url = f"https://graph.facebook.com/{version}/{FACEBOOK_PAGE_ID}"
    params = {
        "fields": "id,name",
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except Exception as exc:
        print(f"WARNING: Facebook capability check request failed: {exc}")
        return

    if not response.ok:
        print(
            "WARNING: Facebook capability check failed. "
            f"HTTP {response.status_code} {response.text[:400]}"
        )
        print(
            "         Verify token scopes and that this Page is subscribed to webhook events."
        )
        return

    try:
        payload = response.json()
    except Exception:
        payload = {}
    page_name = payload.get("name", "")
    print(
        f"Facebook capability check OK for page {payload.get('id', FACEBOOK_PAGE_ID)}"
        + (f" ({page_name})" if page_name else "")
    )


# ============== HEALTH CHECK ==============

@app.route('/', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'running',
        'service': 'Follower Battlegrounds Instagram Webhook',
        'verify_token_configured': bool(VERIFY_TOKEN),
        'access_token_configured': INSTAGRAM_ACCESS_TOKEN_APP != "YOUR_ACCESS_TOKEN_HERE",
        'facebook_features_enabled': _facebook_features_enabled(),
        'facebook_page_configured': bool(FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN),
        'youtube_features_enabled': _youtube_features_enabled(),
        'youtube_poller_enabled': _youtube_poller_enabled(),
    }), 200


@app.route('/status', methods=['GET'])
def status_check():
    """Queue and reply status for monitoring."""
    now = time.time()
    backoff_active = now < _REPLY_BACKOFF_UNTIL
    backoff_remaining = max(0, int(_REPLY_BACKOFF_UNTIL - now))
    with _QUEUE_LOCK:
        pending_count = len(_QUEUE_PENDING)
    with _PROCESSED_LOCK:
        _load_processed_comment_ids()
        processed_count = len(_PROCESSED_COMMENT_IDS)
    return jsonify({
        'status': 'running',
        'pid': os.getpid(),
        'uptime_seconds': int(now - _START_TIME),
        'queue': {
            'size': _REPLY_QUEUE.qsize(),
            'pending_persisted': pending_count,
            'max': REPLY_QUEUE_MAX,
        },
        'reply_rate_seconds': {
            'min': REPLY_RATE_MIN_SECONDS,
            'max': REPLY_RATE_MAX_SECONDS,
        },
        'backoff': {
            'active': backoff_active,
            'remaining_seconds': backoff_remaining,
        },
        'stats': _REPLY_STATS,
        'facebook': {
            'features_enabled': _facebook_features_enabled(),
            'join_capture_enabled': FACEBOOK_ENABLE_JOIN_CAPTURE,
            'result_replies_enabled': FACEBOOK_ENABLE_RESULT_REPLIES,
            'upload_join_comment_enabled': FACEBOOK_UPLOAD_JOIN_COMMENT_ENABLED,
            'page_id_configured': bool(FACEBOOK_PAGE_ID),
            'token_configured': bool(str(FACEBOOK_PAGE_ACCESS_TOKEN or "").strip()),
            'processed_comment_ids': processed_count,
        },
        'youtube': {
            'features_enabled': _youtube_features_enabled(),
            'poller_enabled': _youtube_poller_enabled(),
            'poller_started': _YOUTUBE_POLLER_STARTED,
            'join_capture_enabled': YOUTUBE_ENABLE_JOIN_CAPTURE,
            'result_replies_enabled': YOUTUBE_ENABLE_RESULT_REPLIES,
            'channel_id_configured': bool(str(YOUTUBE_CHANNEL_ID or "").strip()),
            'client_secret_exists': bool(YOUTUBE_CLIENT_SECRET_PATH.exists()),
            'token_exists': bool(YOUTUBE_COMMENT_TOKEN_PATH.exists() or YOUTUBE_UPLOAD_TOKEN_PATH.exists()),
        },
    }), 200


# ============== MAIN ==============

if __name__ == '__main__':
    _ensure_log_dir()
    _restore_queue_from_state()
    _start_heartbeat()
    _facebook_capability_check()
    _youtube_capability_check()
    _start_youtube_comment_poller_if_needed()
    print("\n" + "=" * 60)
    print("Follower Battlegrounds Webhook Server (Instagram + Facebook + YouTube)")
    print("=" * 60)
    print(f"Verify Token: {VERIFY_TOKEN}")
    print(f"Access Token: {'Configured' if INSTAGRAM_ACCESS_TOKEN_APP != 'YOUR_ACCESS_TOKEN_HERE' else 'NOT SET'}")
    print(f"Trigger Keywords: {TRIGGER_KEYWORDS}")
    print(
        "Facebook Page Token: "
        + ("Configured" if str(FACEBOOK_PAGE_ACCESS_TOKEN or "").strip() else "NOT SET")
    )
    print(f"Facebook JOIN capture: {FACEBOOK_ENABLE_JOIN_CAPTURE} | RESULT replies: {FACEBOOK_ENABLE_RESULT_REPLIES}")
    print(f"Facebook JOIN keywords: {FACEBOOK_JOIN_KEYWORDS}")
    print(f"Facebook RESULT keywords: {FACEBOOK_RESULT_KEYWORDS}")
    print(f"Facebook upload JOIN comment: {FACEBOOK_UPLOAD_JOIN_COMMENT_ENABLED}")
    print(
        f"YouTube JOIN capture: {YOUTUBE_ENABLE_JOIN_CAPTURE} | "
        f"RESULT replies: {YOUTUBE_ENABLE_RESULT_REPLIES}"
    )
    print(
        f"YouTube polling: {'ON' if _youtube_poller_enabled() else 'OFF'} | "
        f"interval={max(15.0, float(YOUTUBE_COMMENT_POLL_INTERVAL_SECONDS)):.0f}s"
    )
    print(f"YouTube JOIN keywords: {YOUTUBE_JOIN_KEYWORDS}")
    print(f"YouTube RESULT keywords: {YOUTUBE_RESULT_KEYWORDS}")
    print("=" * 60)
    print("\nNext steps:")
    tunnel_provider = str(getattr(config, "TUNNEL_PROVIDER", "ngrok")).strip().lower()
    if tunnel_provider in ("cloudflare", "cloudflared"):
        tunnel_mode = str(getattr(config, "CLOUDFLARED_TUNNEL_MODE", "quick")).strip().lower()
        hostname = str(getattr(config, "CLOUDFLARED_HOSTNAME", "")).strip()
        if tunnel_mode == "named" and hostname:
            print("1. Ensure cloudflared is running: cloudflared tunnel run <tunnel-name>")
            print("2. In Meta Developer Console, set:")
            print(f"   - Callback URL: https://{hostname}/webhook")
            print(f"   - Verify Token: {VERIFY_TOKEN}")
            print("3. Click 'Verify and save'")
        else:
            print("1. Run cloudflared: cloudflared tunnel --url http://localhost:5000")
            print("2. Copy the https://*.trycloudflare.com URL from output")
            print("3. In Meta Developer Console, set:")
            print("   - Callback URL: <cloudflared-url>/webhook")
            print(f"   - Verify Token: {VERIFY_TOKEN}")
            print("4. Click 'Verify and save'")
    else:
        print("1. Run ngrok: ngrok http 5000")
        print("2. Copy the HTTPS URL from ngrok")
        print("3. In Meta Developer Console, set:")
        print("   - Callback URL: <ngrok-url>/webhook")
        print(f"   - Verify Token: {VERIFY_TOKEN}")
        print("4. Click 'Verify and save'")
    print("=" * 60 + "\n")

    app.run(port=5000, debug=WEBHOOK_DEBUG, use_reloader=WEBHOOK_USE_RELOADER)
