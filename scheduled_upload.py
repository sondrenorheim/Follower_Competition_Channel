#!/usr/bin/env python3
"""
Scheduled Upload Script

Handles timed video uploads with the following rules:
- Waits until 8 AM Norwegian time if games finish earlier
- First video posts immediately at start time
- All videos must be uploaded by 9 PM
- Random intervals between videos (not evenly spaced)
- Starts uploads regardless of start time

Usage:
    python scheduled_upload.py [--background]
"""

import argparse
import datetime
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

try:
    import zoneinfo
    NORWAY_TZ = zoneinfo.ZoneInfo("Europe/Oslo")
except ImportError:
    # Fallback for older Python versions
    import pytz
    NORWAY_TZ = pytz.timezone("Europe/Oslo")

import config

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs" / "scheduled_upload"

# Time boundaries (Norwegian time)
START_HOUR = 8   # 8 AM - earliest upload time
END_HOUR = 21    # 9 PM - all uploads must be done by this time


def get_norway_time() -> datetime.datetime:
    """Get current time in Norwegian timezone."""
    return datetime.datetime.now(NORWAY_TZ)


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


def get_video_count(run_modes: list[str] | None = None) -> int:
    """Count how many game videos will be uploaded."""
    all_modes = run_modes if run_modes is not None else getattr(config, "ALL_GAME_MODES", [])
    return len(all_modes)


def calculate_wait_seconds() -> tuple[int, bool]:
    """
    Calculate how many seconds to wait before starting uploads.

    Returns:
        (seconds_to_wait, should_proceed)
        - seconds_to_wait: How long to wait (0 if ready now)
        - should_proceed: False if it's too late to upload today
    """
    now = get_norway_time()
    current_hour = now.hour

    # If it's after the end hour, roll to next day start
    if current_hour >= END_HOUR:
        next_day = now + datetime.timedelta(days=1)
        target = next_day.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
        wait_seconds = (target - now).total_seconds()
        return int(wait_seconds), True

    # If it's before 8 AM, calculate wait time
    if current_hour < START_HOUR:
        target = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
        wait_seconds = (target - now).total_seconds()
        return int(wait_seconds), True

    # Between 8 AM and end of day - start immediately
    return 0, True


def generate_random_delays(num_videos: int, total_seconds: int) -> list[int]:
    """
    Generate random delays between videos that sum to approximately total_seconds.

    The delays are random but constrained so all videos fit in the time window.
    First video has no delay (uploads immediately).

    Args:
        num_videos: Number of videos to upload
        total_seconds: Total time available for all uploads (in seconds)

    Returns:
        List of delays in seconds (length = num_videos - 1)
    """
    if num_videos <= 1:
        return []

    num_delays = num_videos - 1

    # Reserve some buffer time for actual uploads (estimate ~5 min per video)
    upload_buffer = num_videos * 300  # 5 minutes per video
    available_delay_time = max(0, total_seconds - upload_buffer)

    if available_delay_time <= 0:
        # Not enough time - use minimum delays
        return [300] * num_delays  # 5 minutes between each

    # Generate random proportions
    proportions = [random.random() for _ in range(num_delays)]
    total_proportion = sum(proportions)

    # Scale proportions to fill available time
    delays = [int((p / total_proportion) * available_delay_time) for p in proportions]

    # Ensure minimum delay of 10 minutes between videos
    min_delay = 600  # 10 minutes
    for i in range(len(delays)):
        if delays[i] < min_delay:
            delays[i] = min_delay

    return delays


def format_time(seconds: int) -> str:
    """Format seconds as hours and minutes."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def run_uploads(delays: list[int], background: bool = False, context_file: Path | None = None):
    """
    Run the upload process with pre-calculated delays.

    Args:
        delays: List of delays between videos (in seconds)
        background: If True, run detached from terminal
    """
    # Build the command
    command = [
        sys.executable,
        str(BASE_DIR / "post_run_publish.py"),
        "--skip-stats",
        "--enable-uploads",
        "--ig-uploader", "safe",
        "--ig-export-after-uploads",
        "--wait-for-videos",
        "--wait-max-seconds", "7200",
        "--wait-poll-seconds", "30",
    ]
    if context_file:
        command.extend(["--run-context-file", str(context_file)])

    if bool(getattr(config, "SNAPCHAT_AUTO_UPLOAD", False)):
        command.append("--enable-snapchat-upload")
    if bool(getattr(config, "SNAPCHAT_UPLOAD_ON_IG_FAILURE", False)):
        command.append("--snapchat-upload-on-ig-failure")
    snap_uploader = str(getattr(config, "SNAPCHAT_UPLOADER", "safe") or "safe").strip().lower()
    if snap_uploader in {"api", "safe"}:
        command.extend(["--snapchat-uploader", snap_uploader])
    if snap_uploader == "safe":
        if bool(getattr(config, "SNAPCHAT_HEADLESS", False)):
            command.append("--snapchat-headless")
        snap_cookies_file = str(
            getattr(config, "SNAPCHAT_COOKIES_FILE", "snapchat_cookies.json") or "snapchat_cookies.json"
        ).strip()
        if snap_cookies_file:
            command.extend(["--snapchat-cookies-file", snap_cookies_file])
        snap_profile_dir = str(getattr(config, "SNAPCHAT_PROFILE_DIR", "") or "").strip()
        if snap_profile_dir:
            command.extend(["--snapchat-profile-dir", snap_profile_dir])
    if bool(getattr(config, "X_AUTO_UPLOAD", False)):
        command.append("--enable-x-upload")
    if bool(getattr(config, "X_UPLOAD_ON_IG_FAILURE", False)):
        command.append("--x-upload-on-ig-failure")
    x_uploader = str(getattr(config, "X_UPLOADER", "api") or "api").strip().lower()
    if x_uploader in {"api", "safe"}:
        command.extend(["--x-uploader", x_uploader])
    if x_uploader == "safe":
        if bool(getattr(config, "X_HEADLESS", False)):
            command.append("--x-headless")
        x_cookies_file = str(getattr(config, "X_COOKIES_FILE", "x_cookies.json") or "x_cookies.json").strip()
        if x_cookies_file:
            command.extend(["--x-cookies-file", x_cookies_file])
    if bool(getattr(config, "LEMON8_AUTO_UPLOAD", False)):
        command.append("--enable-lemon8-upload")
    if bool(getattr(config, "LEMON8_UPLOAD_ON_IG_FAILURE", False)):
        command.append("--lemon8-upload-on-ig-failure")
    lemon8_uploader = str(getattr(config, "LEMON8_UPLOADER", "safe") or "safe").strip().lower()
    if lemon8_uploader in {"safe"}:
        command.extend(["--lemon8-uploader", lemon8_uploader])
    if lemon8_uploader == "safe":
        if bool(getattr(config, "LEMON8_HEADLESS", False)):
            command.append("--lemon8-headless")
        lemon8_cookies_file = str(
            getattr(config, "LEMON8_COOKIES_FILE", "lemon8_cookies.json") or "lemon8_cookies.json"
        ).strip()
        if lemon8_cookies_file:
            command.extend(["--lemon8-cookies-file", lemon8_cookies_file])
    if bool(getattr(config, "REDNOTE_AUTO_UPLOAD", False)):
        command.append("--enable-rednote-upload")
    if bool(getattr(config, "REDNOTE_UPLOAD_ON_IG_FAILURE", False)):
        command.append("--rednote-upload-on-ig-failure")
    rednote_uploader = str(getattr(config, "REDNOTE_UPLOADER", "safe") or "safe").strip().lower()
    if rednote_uploader in {"safe"}:
        command.extend(["--rednote-uploader", rednote_uploader])
    if rednote_uploader == "safe":
        if bool(getattr(config, "REDNOTE_HEADLESS", False)):
            command.append("--rednote-headless")
        rednote_cookies_file = str(
            getattr(config, "REDNOTE_COOKIES_FILE", "rednote_cookies.json") or "rednote_cookies.json"
        ).strip()
        if rednote_cookies_file:
            command.extend(["--rednote-cookies-file", rednote_cookies_file])

    # For now, we'll use the average delay approach since post_run_publish
    # doesn't support per-video delays. We pass min/max that covers our range.
    if delays:
        min_delay = min(delays)
        max_delay = max(delays)
        command.extend(["--delay-min-seconds", str(min_delay)])
        command.extend(["--delay-max-seconds", str(max_delay)])

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = get_norway_time()
    log_path = LOG_DIR / f"upload_{now.strftime('%Y%m%d_%H%M%S')}.log"

    print(f"\n{'='*60}")
    print("Starting Upload Process")
    print(f"{'='*60}")
    print(f"Log file: {log_path}")
    print(f"Command: {' '.join(command)}")

    if background:
        try:
            log_file = open(log_path, "a", encoding="utf-8")

            if os.name == "nt":
                flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    creationflags=flags,
                    stdout=log_file,
                    stderr=log_file,
                )
            else:
                subprocess.Popen(
                    command,
                    cwd=str(BASE_DIR),
                    start_new_session=True,
                    stdout=log_file,
                    stderr=log_file,
                )

            print("Upload process started in background.")
            print(f"Check progress in: {log_path}")
            return True
        except Exception as e:
            print(f"Error starting background upload: {e}")
            return False
    else:
        # Run in foreground
        result = subprocess.run(command, cwd=str(BASE_DIR))
        return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Scheduled video upload with timing rules")
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run upload process in background (detached)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without actually uploading"
    )
    parser.add_argument(
        "--context-file",
        type=Path,
        default=None,
        help="Optional run context JSON from main.py (freezes day/modes for uploads).",
    )
    args = parser.parse_args()

    context = load_run_context(args.context_file)
    run_modes = None
    run_day_number = None
    if context:
        modes = context.get("all_game_modes")
        if isinstance(modes, list):
            run_modes = modes
        day_value = context.get("day_number")
        if isinstance(day_value, int):
            run_day_number = day_value

    now = get_norway_time()
    print(f"\n{'='*60}")
    print("Scheduled Upload")
    print(f"{'='*60}")
    print(f"Current time (Norway): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    if run_day_number is not None:
        print(f"Run day number (snapshot): {run_day_number}")

    # Check if we should proceed
    wait_seconds, should_proceed = calculate_wait_seconds()

    # Wait if needed
    if wait_seconds > 0:
        target_time = now + datetime.timedelta(seconds=wait_seconds)
        print(f"\nWaiting until next upload window to start uploads...")
        print(f"Target time: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Wait duration: {format_time(wait_seconds)}")

        if not args.dry_run:
            time.sleep(wait_seconds)
            now = get_norway_time()
            print(f"\nResuming at: {now.strftime('%H:%M:%S')}")

    # Calculate available time until 9 PM
    end_time = now.replace(hour=END_HOUR, minute=0, second=0, microsecond=0)
    if wait_seconds > 0:
        # Recalculate now after waiting
        now = get_norway_time()
        end_time = now.replace(hour=END_HOUR, minute=0, second=0, microsecond=0)

    total_available_seconds = int((end_time - now).total_seconds())

    if total_available_seconds <= 0:
        print("\nERROR: No time remaining until 9 PM deadline.")
        sys.exit(1)

    # Get video count and generate delays
    num_videos = get_video_count(run_modes)
    print(f"\nVideos to upload: {num_videos}")
    print(f"Time available: {format_time(total_available_seconds)} (until 9 PM)")

    delays = generate_random_delays(num_videos, total_available_seconds)

    print(f"\nUpload schedule:")
    print(f"  Video 1: Immediately")

    cumulative = 0
    for i, delay in enumerate(delays, start=2):
        cumulative += delay
        upload_time = now + datetime.timedelta(seconds=cumulative)
        print(f"  Video {i}: ~{upload_time.strftime('%H:%M')} (delay: {format_time(delay)})")

    if delays:
        print(f"\nDelay range: {format_time(min(delays))} - {format_time(max(delays))}")
        print(f"Total delay time: {format_time(sum(delays))}")

    if args.dry_run:
        print("\n[DRY RUN] Would start uploads now.")
        return

    # Start the upload process
    print(f"\n{'='*60}")
    success = run_uploads(delays, background=args.background, context_file=args.context_file)

    if success:
        print("\nUpload process initiated successfully.")
    else:
        print("\nUpload process failed to start.")
        sys.exit(1)


if __name__ == "__main__":
    main()
