#!/usr/bin/env python3
"""
YouTube uploader for the Follower Battlegrounds Shorts channel.

Usage:
    python youtube_uploader.py --video "Videos/Day_30/team_battle_day_30_youtube_short.mp4" --day 30 --game "team_battle"
    python youtube_uploader.py --video "Videos/Day_30/team_battle_day_30_youtube_short.mp4" --day 30 --game "team_battle" --schedule-hours 24
"""

import os
import re
import argparse
import datetime
import pickle
import sys
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

from shared.platform_targets import is_native_youtube_game, normalize_platform_target

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        # Fallback for older Python or if reconfigure fails
        try:
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        except:
            pass  # If all else fails, emojis will be skipped

# ==========================================================
# CONFIG
# ==========================================================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CLIENT_SECRET_PATH = PROJECT_ROOT / "secrets" / "youtube_follower_battlegrounds_client_secret.json"
DEFAULT_TOKEN_PATH = PROJECT_ROOT / "secrets" / "youtube_follower_battlegrounds_token.pickle"
REPO_CLIENT_SECRET_PATH = PROJECT_ROOT / "secrets" / "youtube_client_secret.json"
REPO_TOKEN_PATH = PROJECT_ROOT / "secrets" / "youtube_token.json"
LEGACY_CLIENT_SECRET_PATH = Path(
    r"C:\Users\SondreNorheim\Downloads\client_secret_895049337311-gvm2rt0c0hpe80drohlsgg569f3dhfd8.apps.googleusercontent.com.json"
)
LEGACY_TOKEN_PATH = Path(r"C:\Users\SondreNorheim\Documents\Video_Editor_Script\youtube_token.json")
DEFAULT_INSTAGRAM_HANDLE = os.getenv("YOUTUBE_INSTAGRAM_HANDLE", "@followerbattlegrounds").strip() or "@followerbattlegrounds"
DEFAULT_WEBSITE_URL = os.getenv("YOUTUBE_WEBSITE_URL", "https://www.followerbattlegrounds.com/").strip() or "https://www.followerbattlegrounds.com/"
DEFAULT_JOIN_CTA = os.getenv("YOUTUBE_JOIN_CTA", 'Comment "JOIN" to be added to future games.').strip() or 'Comment "JOIN" to be added to future games.'


def _normalize_path(path_value: str | Path | None) -> Path | None:
    if path_value is None:
        return None
    text = str(path_value).strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _resolve_path(env_var: str, *default_candidates: Path | None) -> Path:
    candidates: list[Path] = []
    env_value = os.getenv(env_var, "").strip()
    if env_value:
        env_path = _normalize_path(env_value)
        if env_path is not None:
            candidates.append(env_path)
    for candidate in default_candidates:
        if candidate is None:
            continue
        normalized = _normalize_path(candidate)
        if normalized is None:
            continue
        candidates.append(normalized)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


CLIENT_SECRET_PATH = _resolve_path(
    "YOUTUBE_CLIENT_SECRET",
    DEFAULT_CLIENT_SECRET_PATH,
    REPO_CLIENT_SECRET_PATH,
    LEGACY_CLIENT_SECRET_PATH,
)
TOKEN_PATH = _resolve_path(
    "YOUTUBE_TOKEN_PATH",
    DEFAULT_TOKEN_PATH,
    REPO_TOKEN_PATH,
    LEGACY_TOKEN_PATH,
)

# Game mode display names
GAME_NAMES = {
    "battle_royale": "Battle Royale",
    "fighter_arena": "Fighter Arena",
    "team_battle": "Team Battle",
    "obstacle_course": "Obstacle Course",
    "platformer_race": "Platformer Race",
    "snake_escape": "Snake Escape",
    "spleef": "Spleef",
    "anime_fighting": "Anime Fighting",
    "gorillas_vs_followers": "Gorillas vs Followers",
    "mini_golf": "Mini Golf",
    "followers_io": "Followers.io",
    "maze_rush": "Maze Rush",
    "flappy_followers": "Flappy Followers",
    "youtube_maze_rush": "Maze Rush",
    "youtube_flappy_followers": "Flappy Followers",
}

# ==========================================================
# AUTH
# ==========================================================
def authenticate_youtube(
    client_secret_path: Path | None = None,
    token_path: Path | None = None,
):
    """Authenticate YouTube once and reuse stored credentials safely."""
    creds = None
    resolved_client_secret = client_secret_path or CLIENT_SECRET_PATH
    resolved_token_path = token_path or TOKEN_PATH

    if not resolved_client_secret.exists():
        raise FileNotFoundError(
            f"YouTube client secret not found: {resolved_client_secret}. "
            "Set YOUTUBE_CLIENT_SECRET or place it in secrets/youtube_follower_battlegrounds_client_secret.json."
        )

    resolved_token_path.parent.mkdir(parents=True, exist_ok=True)

    if resolved_token_path.exists():
        try:
            with open(resolved_token_path, "rb") as token:
                creds = pickle.load(token)
        except (EOFError, pickle.UnpicklingError):
            print("⚠️  Token file corrupted, regenerating...")
            resolved_token_path.unlink(missing_ok=True)

    if not creds or not hasattr(creds, "valid") or not creds.valid:
        if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            print("🔄 Refreshing existing credentials...")
            creds.refresh(Request())
        else:
            print("🔐 Launching browser for Google sign-in...")
            flow = InstalledAppFlow.from_client_secrets_file(str(resolved_client_secret), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(resolved_token_path, "wb") as token:
            pickle.dump(creds, token)
            print(f"💾 Saved new token to {resolved_token_path}")

    print("✅ YouTube authentication successful.")
    return build("youtube", "v3", credentials=creds)

# ==========================================================
# TAG GENERATOR
# ==========================================================
def _get_game_display_name(game_mode: str) -> str:
    return GAME_NAMES.get(game_mode, game_mode.replace("_", " ").title())


def _resolve_metadata_game_mode(game_mode: str, platform_target: str = "instagram") -> str:
    normalized = str(game_mode or "").strip().lower()
    if normalized.startswith("youtube_"):
        candidate = normalized[len("youtube_"):]
        if candidate:
            normalized = candidate
    if is_native_youtube_game(normalized, platform_target):
        return normalized
    return normalized


def _load_video_meta(video_path: Path) -> dict:
    sidecar_path = video_path.with_suffix(f"{video_path.suffix}.meta.json")
    if not sidecar_path.exists():
        return {}
    try:
        import json
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _build_title_prefix(game_mode: str) -> str:
    custom_prefixes = {
        "battle_royale": "I Put Real Followers in a Battle Royale",
        "fighter_arena": "Real Followers Fight in an Arena",
        "team_battle": "Real Followers Fight a Team Battle",
        "obstacle_course": "Real Followers Race This Obstacle Course",
        "platformer_race": "Real Followers Race This Platformer",
        "snake_escape": "Real Followers Try to Survive Snake Escape",
        "spleef": "Real Followers Fight on a Spleef Map",
        "anime_fighting": "Real Followers Enter an Anime Fight",
        "gorillas_vs_followers": "Real Followers Try to Survive the Gorillas",
        "mini_golf": "Real Followers Compete in Mini Golf",
        "followers_io": "Real Followers Battle in Followers.io",
    }
    game_display = _get_game_display_name(game_mode)
    return custom_prefixes.get(game_mode, f"Real Followers Compete in {game_display}")


def generate_tags(game_mode: str, day: int, platform_target: str = "instagram") -> list[str]:
    """Generate compact discovery tags for the YouTube Shorts channel."""
    del day
    metadata_game_mode = _resolve_metadata_game_mode(game_mode, platform_target)
    normalized_platform = normalize_platform_target(platform_target)
    game_display = _get_game_display_name(metadata_game_mode)

    if is_native_youtube_game(metadata_game_mode, normalized_platform):
        game_tags = [
            game_display,
            f"{game_display} Shorts",
            f"{game_display} Challenge",
            "Comment JOIN",
        ]

        generic_tags = [
            "Shorts",
            "Gaming Shorts",
            "Community Game",
            "Join the Next Round",
            "Follower Battlegrounds",
            "Last To Survive",
            "Elimination Challenge",
            "Viewer Challenge",
        ]
    else:
        game_tags = [
            game_display,
            f"{game_display} Shorts",
            f"{game_display} Challenge",
            f"{game_display} Battle",
        ]

        generic_tags = [
            "Shorts",
            "Gaming Shorts",
            "Real Followers Battle",
            "Follower Battlegrounds",
            "Last To Survive",
            "Elimination Challenge",
            "Battle Game",
            "Community Challenge",
        ]

    all_tags = list(dict.fromkeys(game_tags + generic_tags))
    clean_tags = []
    total_len = 0

    for t in all_tags:
        t = re.sub(r"[^A-Za-z0-9\s]", "", t)
        t = re.sub(r"\s+", " ", t.strip())

        if len(t) > 30:
            words = t.split()
            t = " ".join(words[:5])

        if total_len + len(t) + 1 > 490:
            break

        clean_tags.append(t)
        total_len += len(t) + 1

    return clean_tags

# ==========================================================
# TITLE & DESCRIPTION GENERATOR
# ==========================================================
def generate_title(
    game_mode: str,
    day: int,
    platform_target: str = "instagram",
    participant_count: int | None = None,
) -> str:
    """Generate a standalone YouTube-native title."""
    del day
    metadata_game_mode = _resolve_metadata_game_mode(game_mode, platform_target)
    normalized_platform = normalize_platform_target(platform_target)
    if is_native_youtube_game(metadata_game_mode, normalized_platform):
        count_text = (
            f"{max(0, int(participant_count or 0)):,} Players"
            if participant_count
            else "Players"
        )
        title = {
            "maze_rush": f"{count_text} Try to Escape This Maze",
            "flappy_followers": f"{count_text} Try to Survive This Flappy Run",
        }.get(
            metadata_game_mode,
            f"Players Compete in {_get_game_display_name(metadata_game_mode)}",
        )
    else:
        title = f"{_build_title_prefix(metadata_game_mode)} - Only One Survives"
    return title[:100].rstrip(" -|")

def generate_description(
    game_mode: str,
    day: int,
    platform_target: str = "instagram",
    participant_count: int | None = None,
) -> str:
    """Generate a concise Shorts description without series framing."""
    del day
    metadata_game_mode = _resolve_metadata_game_mode(game_mode, platform_target)
    normalized_platform = normalize_platform_target(platform_target)
    game_display = _get_game_display_name(metadata_game_mode)

    if is_native_youtube_game(metadata_game_mode, normalized_platform):
        count_text = (
            f"{max(0, int(participant_count or 0)):,} players"
            if participant_count
            else "Players"
        )
        lines = {
            "maze_rush": [
                f"{count_text} try to escape today's maze.",
                "Only a few make it out.",
            ],
            "flappy_followers": [
                f"{count_text} try to survive today's run.",
                "Last bird alive wins.",
            ],
        }.get(metadata_game_mode, [f"Players compete in {game_display}."])
        lines.extend(
            [
                "",
                DEFAULT_JOIN_CTA,
                "Future YouTube games use people who comment JOIN.",
                f"Stats and results: {DEFAULT_WEBSITE_URL}",
                "",
                "#shorts #gaming #communitygame #join #followerbattlegrounds",
            ]
        )
    else:
        lines = [
            "Every dot is a real follower.",
            f"Only one survives this {game_display.lower()}.",
            "",
            f"Watch real followers compete in {game_display}.",
            DEFAULT_JOIN_CTA,
            f"Instagram: {DEFAULT_INSTAGRAM_HANDLE}",
            f"Stats and results: {DEFAULT_WEBSITE_URL}",
            "",
            "#shorts #gaming #followerbattlegrounds #battle #creatorgames",
        ]
    return "\n".join(lines)

# ==========================================================
# UPLOAD FUNCTION
# ==========================================================
def upload_video(youtube, video_path, title, description, publish_time=None, tags=None, thumbnail_path=None, privacy="public"):
    """
    Upload a video to YouTube and optionally schedule it.
    Gracefully handles quota and invalid tag errors.
    """
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": "20",  # Gaming category
        },
        "status": {"privacyStatus": privacy},
    }

    if publish_time:
        body["status"]["publishAt"] = publish_time.isoformat() + "Z"
        body["status"]["privacyStatus"] = "private"  # Required for scheduling

    print(f"\n🎥 Uploading video: {title}")
    print(f"📝 Tags: {', '.join(tags or [])[:150]}... ({len(tags or [])} total)")
    print(f"🔒 Privacy: {privacy}")

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    try:
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploading... {int(status.progress() * 100)}%")

        video_id = response.get("id")
        print(f"✅ Uploaded successfully! Video ID: {video_id}")
        print(f"🔗 Video URL: https://www.youtube.com/watch?v={video_id}")

        # Upload thumbnail if provided
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"📸 Uploading thumbnail...")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("✅ Thumbnail uploaded successfully.")

        if publish_time:
            print(f"⏰ Scheduled for {publish_time.isoformat()} UTC")
        else:
            print(f"✅ Video is {privacy}.")

        return video_id

    except HttpError as e:
        error_str = str(e)
        if "uploadLimitExceeded" in error_str:
            print("⚠️  YouTube upload limit reached. Skipping this upload (will retry next run).")
            return None
        if "invalidTags" in error_str:
            print("⚠️  YouTube rejected tags — re-running without them.")
            body["snippet"]["tags"] = []
            retry = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            while response is None:
                status, response = retry.next_chunk()
            video_id = response.get("id")
            print(f"✅ Uploaded successfully (without tags)! Video ID: {video_id}")
            return video_id
        raise

# ==========================================================
# MAIN
# ==========================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload Follower Battlegrounds Shorts to YouTube.")
    parser.add_argument("--video", required=True, help="Path to the video file.")
    parser.add_argument("--day", type=int, required=True, help="Day number of the competition.")
    parser.add_argument("--game", required=True, help="Game mode (e.g., team_battle, battle_royale).")
    parser.add_argument("--thumbnail", help="Path to custom thumbnail (optional).")
    parser.add_argument(
        "--client-secret-path",
        help="Optional OAuth client secret path for the new YouTube channel.",
    )
    parser.add_argument(
        "--token-path",
        help="Optional token cache path so the new channel stays separate from older uploads.",
    )
    parser.add_argument("--schedule-hours", type=float, default=0, help="Schedule delay in hours (0 = upload as private immediately).")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="public", help="Privacy status (default: public).")
    parser.add_argument("--custom-title", help="Custom title (overrides auto-generated).")
    parser.add_argument("--custom-description", help="Custom description (overrides auto-generated).")
    parser.add_argument("--platform", choices=["instagram", "youtube"], default="instagram", help="Metadata platform target.")
    args = parser.parse_args()

    # Validate video exists
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ Error: Video not found: {video_path}")
        exit(1)

    print("=" * 70)
    print("🎬 FOLLOWER BATTLEGROUNDS YOUTUBE SHORTS UPLOADER")
    print("=" * 70)
    print(f"Video: {video_path.name}")
    print(f"Game: {args.game}")
    print(f"Day: {args.day}")
    print("=" * 70)

    # Authenticate
    youtube = authenticate_youtube(
        client_secret_path=_normalize_path(args.client_secret_path),
        token_path=_normalize_path(args.token_path),
    )

    # Generate title and description
    video_meta = _load_video_meta(video_path)
    participant_count = video_meta.get("requested_count")
    title = args.custom_title or generate_title(args.game, args.day, args.platform, participant_count)
    description = args.custom_description or generate_description(args.game, args.day, args.platform, participant_count)
    tags = generate_tags(args.game, args.day, args.platform)

    # Calculate publish time if scheduling
    publish_time = None
    if args.schedule_hours > 0:
        publish_time = datetime.datetime.utcnow() + datetime.timedelta(hours=args.schedule_hours)

    # Upload
    video_id = upload_video(
        youtube,
        video_path=str(video_path),
        title=title,
        description=description,
        publish_time=publish_time,
        tags=tags,
        thumbnail_path=args.thumbnail,
        privacy=args.privacy
    )

    if video_id:
        print("\n" + "=" * 70)
        print("✅ UPLOAD COMPLETE")
        print("=" * 70)
        print(f"Video ID: {video_id}")
        print(f"URL: https://www.youtube.com/watch?v={video_id}")
        print("=" * 70)
    else:
        print("\n⚠️  Upload skipped due to quota limits.")
        exit(0)
