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
import time
import random
import webbrowser
from functools import lru_cache
from pathlib import Path

import config
from shared import auto_push, statistics, game_history
from instagrapi import Client
from shared import statistics, game_history


def build_video_path(game_mode: str) -> Path:
    """
    Build the expected video output path for a game mode using the config helper.
    Assumes TEST_MODE was False when videos were generated.
    """
    filename = config.get_output_video_path(game_mode=game_mode, day_number=config.DAY_NUMBER, test_mode=False)
    return Path(filename)


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


def upload_videos(cl: Client, video_paths: list[Path], caption_template: str, delay_seconds: int):
    for idx, video_path in enumerate(video_paths):
        if not video_path.exists():
            print(f"⚠️ Skipping missing video: {video_path}")
            continue
        game_mode = video_path.stem.split("_day_")[0] if "_day_" in video_path.stem else video_path.stem
        caption = caption_template.format(game_mode=game_mode, day_number=config.DAY_NUMBER)
        top_users = get_top_usernames_for_game(config.DAY_NUMBER, game_mode, limit=10)
        caption += format_top_users_block(top_users)
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


def save_instagram_cookies(cookies_file: Path) -> bool:
    try:
        from safe_instagram_uploader import SafeInstagramUploader
    except Exception as e:
        print(f"IG safe uploader unavailable: {e}")
        return False
    uploader = SafeInstagramUploader(cookies_file=str(cookies_file), headless=False)
    uploader.save_cookies()
    return True


def upload_instagram_safe(video_path: Path, caption: str, cookies_file: Path, headless: bool) -> bool:
    try:
        from safe_instagram_uploader import SafeInstagramUploader
    except Exception as e:
        print(f"IG safe uploader unavailable: {e}")
        return False
    uploader = SafeInstagramUploader(cookies_file=str(cookies_file), headless=headless)
    return uploader.upload_reel(str(video_path), caption)


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


def upload_youtube(video_path: Path, game_mode: str, day_number: int, schedule_hours: int = 0, privacy: str = "private") -> bool:
    """
    Upload to YouTube using the same channel as movie pipeline.

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
        print(f"❌ YouTube uploader not found: {youtube_uploader}")
        return False

    if not video_path.exists():
        print(f"⚠️ Skipping missing video for YouTube: {video_path}")
        return False

    schedule_msg = f" (scheduled {schedule_hours}h from now)" if schedule_hours > 0 else f" (privacy: {privacy})"
    print(f"▶️ Uploading to YouTube{schedule_msg}...")

    cmd = [
        "python",
        str(youtube_uploader),
        "--video", str(video_path),
        "--day", str(day_number),
        "--game", game_mode,
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
            timeout=600,  # 10 minute timeout for YouTube
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print(f"✅ YouTube upload successful!")
            return True
        else:
            print(f"❌ YouTube upload failed (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print("❌ YouTube upload timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        return False


def push_stats(commit_message: str | None):
    if getattr(config, "TEST_MODE", False):
        raise SystemExit("TEST_MODE is True: stats/history not saved. Re-run games with TEST_MODE=False before pushing.")
    # Regenerate web bundles before pushing
    try:
        stats = statistics.PlayerStatistics()
        stats.export_web_stats(output_path="website/public/player_statistics_web.json")
        print("Regenerated website/public/player_statistics_web.json")
    except Exception as e:
        print(f"Failed to regenerate player_statistics_web.json: {e}")
    try:
        gh = game_history.GameHistory("game_history.json")
        gh.export_web_history(output_path="website/public/game_history_web.json")
        print("Regenerated website/public/game_history_web.json")
    except Exception as e:
        print(f"Failed to regenerate game_history.json (web): {e}")
    ok = auto_push.push_stats_to_github(commit_message=commit_message)
    if not ok:
        raise SystemExit("Git push failed. See logs above.")


def parse_args():
    parser = argparse.ArgumentParser(description="Push stats to GitHub and upload generated videos as Reels.")
    parser.add_argument(
        "--enable-uploads",
        action="store_true",
        help="Enable Instagram/TikTok/YouTube uploads (default: stats only).",
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
        default=Path(r"C:\Users\SondreNorheim\Documents\Instagram-Reels-Scraper-Auto-Poster\src\session_followerbattlegrounds.json"),
        help="Path to instagrapi session JSON (or set IG_SESSION_FILE env var).",
    )
    parser.add_argument(
        "--tiktok-session-file",
        type=Path,
        default=Path(r"C:\Users\SondreNorheim\Documents\tiktok_follower_account_sessionid.json"),
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
        help="Fixed delay between uploads in seconds. If set, randomization of ±20%% will be applied.",
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
        "--skip-youtube",
        action="store_true",
        help="Skip YouTube uploads (only upload to Instagram/TikTok).",
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
    return parser.parse_args()

def load_export_password_from_file(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""

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

    # Build expected videos from ALL_GAME_MODES
    game_modes = getattr(config, "ALL_GAME_MODES", [])
    video_paths = [build_video_path(gm) for gm in game_modes]

    if args.skip_stats:
        print("⚠️ Skipping stats/history push (--skip-stats).")
    else:
        print("📦 Pushing stats/history to GitHub...")
        push_stats(args.push_message)

    if not args.enable_uploads:
        if args.skip_stats:
            print("✅ Done (stats skipped, video upload disabled).")
        else:
            print("✅ Done (stats pushed only - video upload disabled).")
        return

    session_path = os.getenv("IG_SESSION_FILE", str(args.session_file))
    if not session_path:
        raise SystemExit("Missing session file. Provide --session-file or set IG_SESSION_FILE.")
    session_path = Path(session_path)
    ig_cookies_path = Path(os.getenv("IG_COOKIES_FILE", str(args.ig_cookies_file)))
    tiktok_session_path = os.getenv("TIKTOK_SESSION_FILE", str(args.tiktok_session_file))

    ig_safe = None
    ig_export = None

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
    if args.ig_uploader == "instagrapi":
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
            print(f"⚠️ TikTok session load failed: {e}. TikTok uploads will be skipped.")

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

    print("📤 Uploading videos as Reels/TikTok/YouTube...")
    try:
        if args.ig_uploader == "safe":
            from safe_instagram_uploader import SafeInstagramUploader
            ig_safe = SafeInstagramUploader(
                cookies_file=str(ig_cookies_path),
                headless=args.ig_headless,
            )
            if not ig_safe.start_session():
                raise SystemExit("Failed to start safe Instagram session.")

        for idx, video_path in enumerate(video_paths):
            if not video_path.exists():
                print(f"⚠️ Skipping missing video: {video_path}")
                continue
            game_mode = video_path.stem.split("_day_")[0] if "_day_" in video_path.stem else video_path.stem
            base_caption = args.caption_template.format(game_mode=game_mode, day_number=config.DAY_NUMBER)
            top_users = get_top_usernames_for_game(config.DAY_NUMBER, game_mode, limit=10)
            ig_caption = base_caption + format_top_users_block(top_users)

            # Instagram upload
            print(f"▶️ IG: Uploading {video_path.name}")
            if args.ig_uploader == "safe":
                ig_safe.upload_reel(str(video_path), ig_caption, reuse_session=True)
            else:
                upload_instagram(client, video_path, ig_caption)

            # TikTok upload
            if tiktok_session_id:
                print(f"▶️ TikTok: Uploading {video_path.name}")
                upload_tiktok(tiktok_session_id, video_path, base_caption)

            # YouTube upload
            skip_youtube_modes = set(getattr(config, "YOUTUBE_SKIP_GAME_MODES", []))
            if not args.skip_youtube and game_mode not in skip_youtube_modes:
                print(f"▶️ YouTube: Uploading {video_path.name}")
                upload_youtube(
                    video_path=video_path,
                    game_mode=game_mode,
                    day_number=config.DAY_NUMBER,
                    schedule_hours=args.youtube_schedule_hours,
                    privacy=args.youtube_privacy
                )
            elif game_mode in skip_youtube_modes:
                print(f"Skipping YouTube upload for {game_mode} (config.YOUTUBE_SKIP_GAME_MODES).")

            # Delay before next upload (except after last one)
            if idx < len(video_paths) - 1:
                randomized_delay = None
                if args.delay_seconds is not None and args.delay_seconds > 0:
                    variation = args.delay_seconds * 0.2
                    randomized_delay = args.delay_seconds + random.uniform(-variation, variation)
                elif args.delay_min_seconds and args.delay_max_seconds:
                    low = min(args.delay_min_seconds, args.delay_max_seconds)
                    high = max(args.delay_min_seconds, args.delay_max_seconds)
                    randomized_delay = random.uniform(low, high)

                if randomized_delay and randomized_delay > 0:
                    print(f"⏳ Waiting {randomized_delay/3600:.2f} hours before next upload...")
                    time.sleep(randomized_delay)

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
        if ig_export:
            ig_export.close_session()

    print("✅ Done.")


if __name__ == "__main__":
    main()
