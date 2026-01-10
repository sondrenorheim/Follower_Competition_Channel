#!/usr/bin/env python3
"""
YouTube Uploader for Follower Competition Channel
Uploads follower battle videos to the same YouTube channel as movie summaries.

Usage:
    python youtube_uploader.py --video "Videos/Day_30/team_battle_day_30.mp4" --day 30 --game "team_battle"
    python youtube_uploader.py --video "Videos/Day_30/team_battle_day_30.mp4" --day 30 --game "team_battle" --schedule-hours 24
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
# CONFIG - Using same credentials as movie pipeline
# ==========================================================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_PATH = r"C:\Users\SondreNorheim\Downloads\client_secret_895049337311-gvm2rt0c0hpe80drohlsgg569f3dhfd8.apps.googleusercontent.com.json"
TOKEN_PATH = Path(r"C:\Users\SondreNorheim\Documents\Video_Editor_Script\youtube_token.json")

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
}

# ==========================================================
# AUTH
# ==========================================================
def authenticate_youtube():
    """Authenticate YouTube once and reuse stored credentials safely."""
    creds = None

    if TOKEN_PATH.exists():
        try:
            with open(TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)
        except (EOFError, pickle.UnpicklingError):
            print("⚠️  Token file corrupted, regenerating...")
            TOKEN_PATH.unlink(missing_ok=True)

    if not creds or not hasattr(creds, "valid") or not creds.valid:
        if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            print("🔄 Refreshing existing credentials...")
            creds.refresh(Request())
        else:
            print("🔐 Launching browser for Google sign-in...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)
            print(f"💾 Saved new token to {TOKEN_PATH}")

    print("✅ YouTube authentication successful.")
    return build("youtube", "v3", credentials=creds)

# ==========================================================
# TAG GENERATOR
# ==========================================================
def generate_tags(game_mode: str, day: int) -> list[str]:
    """Generate SEO-friendly tags for follower battle videos."""
    game_display = GAME_NAMES.get(game_mode, game_mode.replace("_", " ").title())

    # Game-specific tags
    game_tags = [
        game_display,
        f"{game_display} Day {day}",
        f"Instagram {game_display}",
        f"Follower {game_display}",
    ]

    # Generic channel/series tags
    generic_tags = [
        "Follower Battle Royale",
        "Follower Competition",
        "Instagram Followers",
        "Follower Challenge",
        "Instagram Game",
        "Social Media Battle",
        "Follower Battle",
        "Instagram Competition",
        "Follower Tournament",
        "Instagram Followers Game",
        "Real Followers Battle",
        "FollowerBattlegrounds",
        "Interactive Competition",
        "Community Game",
    ]

    all_tags = list(dict.fromkeys(game_tags + generic_tags))
    clean_tags = []
    total_len = 0

    for t in all_tags:
        # Clean tag
        t = re.sub(r"[^A-Za-z0-9\s]", "", t)
        t = re.sub(r"\s+", " ", t.strip())

        # Truncate if too long (YouTube limit: 30 chars per tag)
        if len(t) > 30:
            words = t.split()
            t = " ".join(words[:5])

        # Check total length (YouTube limit: 500 chars total)
        if total_len + len(t) + 1 > 490:
            break

        clean_tags.append(t)
        total_len += len(t) + 1

    return clean_tags

# ==========================================================
# TITLE & DESCRIPTION GENERATOR
# ==========================================================
def generate_title(game_mode: str, day: int) -> str:
    """Generate engaging title for the video."""
    game_display = GAME_NAMES.get(game_mode, game_mode.replace("_", " ").title())
    return f"Follower {game_display} - Day {day} | Real Instagram Followers Battle!"

def generate_description(game_mode: str, day: int) -> str:
    """Generate detailed description for the video."""
    game_display = GAME_NAMES.get(game_mode, game_mode.replace("_", " ").title())

    description = f"""Watch real Instagram followers compete in an epic {game_display}!

🎮 Day {day} of the Follower Competition
👥 Featuring REAL Instagram followers
🏆 Who will win today's battle?

In this video, Instagram followers battle it out in a {game_display.lower()} competition. Each player represents a real follower from our community!

📊 Check out the full leaderboard and statistics at:
https://www.followerbattlegrounds.com/

Want to see yourself in the next video? Follow us on Instagram @followerbattlegrounds!

#FollowerBattle #InstagramFollowers #Competition #Gaming #BattleRoyale #Community

🎬 Follower Battle Royale Series
New battles every day featuring YOUR Instagram followers!
"""
    return description

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
    parser = argparse.ArgumentParser(description="Upload follower battle videos to YouTube.")
    parser.add_argument("--video", required=True, help="Path to the video file.")
    parser.add_argument("--day", type=int, required=True, help="Day number of the competition.")
    parser.add_argument("--game", required=True, help="Game mode (e.g., team_battle, battle_royale).")
    parser.add_argument("--thumbnail", help="Path to custom thumbnail (optional).")
    parser.add_argument("--schedule-hours", type=float, default=0, help="Schedule delay in hours (0 = upload as private immediately).")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="public", help="Privacy status (default: public).")
    parser.add_argument("--custom-title", help="Custom title (overrides auto-generated).")
    parser.add_argument("--custom-description", help="Custom description (overrides auto-generated).")
    args = parser.parse_args()

    # Validate video exists
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ Error: Video not found: {video_path}")
        exit(1)

    print("=" * 70)
    print("🎬 FOLLOWER COMPETITION YOUTUBE UPLOADER")
    print("=" * 70)
    print(f"Video: {video_path.name}")
    print(f"Game: {args.game}")
    print(f"Day: {args.day}")
    print("=" * 70)

    # Authenticate
    youtube = authenticate_youtube()

    # Generate title and description
    title = args.custom_title or generate_title(args.game, args.day)
    description = args.custom_description or generate_description(args.game, args.day)
    tags = generate_tags(args.game, args.day)

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
