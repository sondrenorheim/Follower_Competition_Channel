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
import os
import time
import random
from pathlib import Path

import config
from shared import auto_push
from instagrapi import Client


def build_video_path(game_mode: str) -> Path:
    """
    Build the expected video output path for a game mode using the config helper.
    Assumes TEST_MODE was False when videos were generated.
    """
    filename = config.get_output_video_path(game_mode=game_mode, day_number=config.DAY_NUMBER, test_mode=False)
    return Path(filename)


def load_client(session_file: Path) -> Client:
    if not session_file.exists():
        raise FileNotFoundError(f"Session file not found: {session_file}")
    cl = Client()
    cl.load_settings(session_file)
    cl.get_timeline_feed()  # sanity check
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


def upload_videos(cl: Client, video_paths: list[Path], caption_template: str, delay_seconds: int):
    for idx, video_path in enumerate(video_paths):
        if not video_path.exists():
            print(f"⚠️ Skipping missing video: {video_path}")
            continue
        game_mode = video_path.stem.split("_day_")[0] if "_day_" in video_path.stem else video_path.stem
        caption = caption_template.format(game_mode=game_mode, day_number=config.DAY_NUMBER)
        print(f"▶️ Uploading {video_path} as Reel with caption:\n{caption}")
        media = cl.clip_upload(str(video_path), caption=caption)
        print(f"✅ Uploaded: {video_path.name} -> {media.pk}")

        # Delay handled after TikTok upload
def upload_instagram(cl: Client, video_path: Path, caption: str) -> bool:
    try:
        media = cl.clip_upload(str(video_path), caption=caption)
        print(f"✅ IG uploaded: {video_path.name} -> {media.pk}")
        return True
    except Exception as e:
        print(f"⚠️ IG upload failed for {video_path.name}: {e}")
        # One retry after longer delay (avoid automation detection)
        try:
            retry_delay = random.randint(30, 60)  # 30-60 seconds
            print(f"   Waiting {retry_delay}s before retry...")
            time.sleep(retry_delay)
            media = cl.clip_upload(str(video_path), caption=caption)
            print(f"✅ IG uploaded on retry: {video_path.name} -> {media.pk}")
            return True
        except Exception as e2:
            print(f"❌ IG upload retry failed for {video_path.name}: {e2}")
            return False


def upload_tiktok_cookie_based(video_path: Path, caption: str, username: str = "SingingNarrator", schedule_hours: int = 0):
    """
    Upload to TikTok using TiktokAutoUploader (cookie-based, more reliable)
    """
    # Use local TiktokAutoUploader in this project
    uploader_dir = Path(__file__).parent / "TiktokAutoUploader"
    cli_script = uploader_dir / "cli.py"

    if not cli_script.exists():
        print(f"❌ TiktokAutoUploader not found at: {uploader_dir}")
        print("   Install it or update the path in post_run_publish.py")
        return False

    if not video_path.exists():
        print(f"⚠️ Skipping missing video for TikTok: {video_path}")
        return False

    # Check if cookie file exists
    cookie_path = uploader_dir / "CookiesDir" / f"tiktok_session-{username}.cookie"
    if not cookie_path.exists():
        print(f"❌ TikTok cookie not found: {cookie_path}")
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
        print(f"📋 Copied video to TikTok uploader folder")
    except Exception as e:
        print(f"❌ Failed to copy video: {e}")
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

    print(f"▶️ Uploading to TikTok{schedule_msg}...")

    try:
        import subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
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
            print(f"✅ TikTok upload successful!")
            return True
        else:
            print(f"❌ TikTok upload failed (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print("❌ TikTok upload timed out after 5 minutes")
        # Clean up
        try:
            temp_video_path.unlink()
        except:
            pass
        return False
    except Exception as e:
        print(f"❌ TikTok upload failed: {e}")
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


def push_stats(commit_message: str | None):
    if getattr(config, "TEST_MODE", False):
        raise SystemExit("TEST_MODE is True: stats/history not saved. Re-run games with TEST_MODE=False before pushing.")
    ok = auto_push.push_stats_to_github(commit_message=commit_message)
    if not ok:
        raise SystemExit("Git push failed. See logs above.")


def parse_args():
    parser = argparse.ArgumentParser(description="Push stats to GitHub and upload generated videos as Reels.")
    parser.add_argument(
        "--session-file",
        type=Path,
        default=Path(r"C:\Users\SondreNorheim\Documents\Instagram-Reels-Scraper-Auto-Poster\src\session_followerbattlegrounds.json"),
        help="Path to instagrapi session JSON (or set IG_SESSION_FILE env var).",
    )
    parser.add_argument(
        "--tiktok-session-file",
        type=Path,
        default=Path(r"C:\Users\SondreNorheim\Documents\tiktok_follower_account_sessionid.json"),
        help="Path to TikTok session JSON with {'sessionid': '...'} (or set TIKTOK_SESSION_FILE env var).",
    )
    parser.add_argument(
        "--caption-template",
        default="Day {day_number} of making my followers battle every day! Follow to enter the battle 🥊\n\nCheck the link in the bio for your result and overall monthly ranking!\n\n#followerbattlegrounds",
        help="Caption template; placeholders: {game_mode}, {day_number}.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=int,
        default=14400,
        help="Delay between uploads in seconds (default 14400 = 4 hours). Randomization of ±20%% will be applied.",
    )
    parser.add_argument(
        "--push-message",
        default=None,
        help="Optional git commit message for stats push.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    # Session files not needed when video upload is disabled
    # session_path = args.session_file or os.getenv("IG_SESSION_FILE")
    # if not session_path:
    #     raise SystemExit("Missing session file. Provide --session-file or set IG_SESSION_FILE.")
    # session_path = Path(session_path)
    # tiktok_session_path = args.tiktok_session_file or os.getenv("TIKTOK_SESSION_FILE")

    # Build expected videos from ALL_GAME_MODES
    game_modes = getattr(config, "ALL_GAME_MODES", [])
    video_paths = [build_video_path(gm) for gm in game_modes]

    print("📦 Pushing stats/history to GitHub...")
    push_stats(args.push_message)

    # VIDEO UPLOAD DISABLED - Only pushing stats to GitHub
    # Uncomment the section below to re-enable video uploads
    """
    print("📤 Uploading videos as Reels/TikTok...")
    client = load_client(session_path)
    tiktok_session_id = None
    if tiktok_session_path:
        try:
            tiktok_session_id = load_tiktok_session(Path(tiktok_session_path))
        except Exception as e:
            print(f"⚠️ TikTok session load failed: {e}. TikTok uploads will be skipped.")

    for idx, video_path in enumerate(video_paths):
        if not video_path.exists():
            print(f"⚠️ Skipping missing video: {video_path}")
            continue
        game_mode = video_path.stem.split("_day_")[0] if "_day_" in video_path.stem else video_path.stem
        caption = args.caption_template.format(game_mode=game_mode, day_number=config.DAY_NUMBER)

        # Instagram upload
        print(f"▶️ IG: Uploading {video_path.name}")
        ig_ok = upload_instagram(client, video_path, caption)

        # TikTok upload
        if tiktok_session_id:
            print(f"▶️ TikTok: Uploading {video_path.name}")
            upload_tiktok(tiktok_session_id, video_path, caption)

        # Delay before next upload (except after last one)
        # Add randomization to avoid automation detection
        if args.delay_seconds > 0 and idx < len(video_paths) - 1:
            # Add ±20% randomization to delay (e.g., 3 hours ± 36 minutes)
            variation = args.delay_seconds * 0.2
            randomized_delay = args.delay_seconds + random.uniform(-variation, variation)
            print(f"⏳ Waiting {randomized_delay/3600:.2f} hours before next upload...")
            time.sleep(randomized_delay)
    """

    print("✅ Done (stats pushed only - video upload disabled).")


if __name__ == "__main__":
    main()
