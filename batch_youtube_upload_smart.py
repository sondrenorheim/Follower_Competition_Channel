#!/usr/bin/env python3
"""
Smart Batch YouTube Upload with Quota Handling
Uploads videos with scheduling, automatically retries when quota limits are hit.

Usage:
    # Start from Day 13 with 2-hour spacing, auto-retry on quota
    python batch_youtube_upload_smart.py --start-day 13 --spacing-hours 2

    # Dry run first
    python batch_youtube_upload_smart.py --start-day 13 --spacing-hours 2 --dry-run
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
VIDEOS_ROOT = Path("Videos")
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}

# YouTube quota limits (typically resets at midnight Pacific Time)
QUOTA_SLEEP_HOURS = 4  # Sleep for 4 hours when quota is hit
QUOTA_MAX_RETRIES = 6  # Retry up to 6 times (= 24 hours total)

# Game mode detection
GAME_MODE_PATTERNS = {
    "battle_royale": "battle_royale",
    "fighter_arena": "fighter_arena",
    "team_battle": "team_battle",
    "obstacle_course": "obstacle_course",
    "platformer_race": "platformer_race",
    "snake_escape": "snake_escape",
    "spleef": "spleef",
    "anime_fighting": "anime_fighting",
    "gorillas_vs_followers": "gorillas_vs_followers",
    "followers_io": "followers_io",
}


def find_day_folders(start_day: int, end_day: int = None):
    """Find all Day_XX folders in the Videos directory."""
    day_folders = []

    if end_day is None:
        for folder in sorted(VIDEOS_ROOT.glob("Day_*")):
            if folder.is_dir():
                try:
                    day_num = int(folder.name.split("_")[1])
                    if day_num >= start_day:
                        day_folders.append((day_num, folder))
                except (IndexError, ValueError):
                    continue
    else:
        for day_num in range(start_day, end_day + 1):
            folder = VIDEOS_ROOT / f"Day_{day_num}"
            if folder.exists() and folder.is_dir():
                day_folders.append((day_num, folder))

    return sorted(day_folders)


def find_videos_in_folder(folder: Path):
    """Find all video files in a folder and detect game mode."""
    videos = []

    for video_file in sorted(folder.glob("*")):
        if video_file.suffix.lower() not in VIDEO_EXTS:
            continue

        game_mode = None
        filename_lower = video_file.stem.lower()

        for pattern, mode in GAME_MODE_PATTERNS.items():
            if pattern in filename_lower:
                game_mode = mode
                break

        if not game_mode:
            print(f"⚠️  Could not detect game mode for: {video_file.name}")
            continue

        videos.append((video_file, game_mode))

    return videos


def upload_video(video_path: Path, day: int, game_mode: str, schedule_hours: int, privacy: str, dry_run: bool = False):
    """
    Upload a single video to YouTube.

    Returns:
        tuple: (success: bool, quota_hit: bool)
    """
    youtube_uploader = Path(__file__).parent / "youtube_uploader.py"

    if not youtube_uploader.exists():
        print(f"❌ YouTube uploader not found: {youtube_uploader}")
        return False, False

    if dry_run:
        publish_time = datetime.now() + timedelta(hours=schedule_hours)
        print(f"   [DRY RUN] Would upload: {video_path.name}")
        print(f"   [DRY RUN] Game: {game_mode}, Day: {day}")
        print(f"   [DRY RUN] Schedule: {schedule_hours}h ({publish_time.strftime('%Y-%m-%d %H:%M')})")
        print(f"   [DRY RUN] Privacy: {privacy}")
        return True, False

    cmd = [
        "python",
        str(youtube_uploader),
        "--video", str(video_path),
        "--day", str(day),
        "--game", game_mode,
        "--privacy", privacy,
    ]

    if schedule_hours > 0:
        cmd.extend(["--schedule-hours", str(schedule_hours)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=600,
        )

        # Check for quota limit in output
        output = (result.stdout or "") + (result.stderr or "")
        quota_hit = "upload limit reached" in output.lower() or "quota" in output.lower()

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            return True, quota_hit
        else:
            return False, quota_hit

    except subprocess.TimeoutExpired:
        print("❌ Upload timed out after 10 minutes")
        return False, False
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False, False


def save_progress(video_index: int, schedule_offset_hours: int, progress_file: Path):
    """Save current progress to file."""
    progress = {
        "video_index": video_index,
        "schedule_offset_hours": schedule_offset_hours,
        "timestamp": datetime.now().isoformat()
    }
    import json
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)


def load_progress(progress_file: Path):
    """Load progress from file."""
    if not progress_file.exists():
        return None
    try:
        import json
        with open(progress_file, 'r') as f:
            return json.load(f)
    except:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Smart batch upload with automatic quota retry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload from Day 13 onwards with 2-hour spacing (auto-retry on quota)
  python batch_youtube_upload_smart.py --start-day 13 --spacing-hours 2

  # Resume from previous run
  python batch_youtube_upload_smart.py --resume
        """
    )
    parser.add_argument("--start-day", type=int, help="Starting day number (e.g., 13)")
    parser.add_argument("--end-day", type=int, help="Ending day number (optional)")
    parser.add_argument("--spacing-hours", type=int, default=2, help="Hours between each video upload (default: 2)")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="public", help="Privacy status (default: public)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--resume", action="store_true", help="Resume from last saved progress")
    parser.add_argument("--quota-sleep-hours", type=int, default=QUOTA_SLEEP_HOURS, help="Hours to sleep when quota is hit (default: 4)")

    args = parser.parse_args()

    progress_file = Path("youtube_upload_progress.json")

    # Resume mode
    if args.resume:
        progress = load_progress(progress_file)
        if not progress:
            print("❌ No saved progress found. Start a new upload instead.")
            sys.exit(1)

        print("=" * 70)
        print("🔄 RESUMING PREVIOUS UPLOAD")
        print("=" * 70)
        print(f"Last save: {progress['timestamp']}")
        print(f"Resuming from video #{progress['video_index'] + 1}")
        print("=" * 70)
        # For resume, we need to re-scan folders (not ideal but works)
        print("\n⚠️  Resume requires --start-day. Please specify original start day.")
        sys.exit(1)

    if not args.start_day:
        parser.error("--start-day is required (unless using --resume)")

    print("=" * 70)
    print("📹 SMART BATCH YOUTUBE UPLOAD WITH QUOTA HANDLING")
    print("=" * 70)
    print(f"Start Day: {args.start_day}")
    print(f"End Day: {args.end_day or 'All available'}")
    print(f"Spacing: {args.spacing_hours} hours between videos")
    print(f"Privacy: {args.privacy}")
    print(f"Quota retry: Sleep {args.quota_sleep_hours}h when limit hit")
    if args.dry_run:
        print("🧪 DRY RUN MODE - No actual uploads will occur")
    print("=" * 70)
    print()

    # Find all day folders
    day_folders = find_day_folders(args.start_day, args.end_day)

    if not day_folders:
        print(f"❌ No day folders found starting from Day {args.start_day}")
        sys.exit(1)

    print(f"📂 Found {len(day_folders)} day folder(s)")

    # Collect all videos
    all_uploads = []
    for day_num, folder in day_folders:
        videos = find_videos_in_folder(folder)
        for video_file, game_mode in videos:
            all_uploads.append((video_file, day_num, game_mode))

    if not all_uploads:
        print("\n❌ No videos found to upload!")
        sys.exit(1)

    print(f"📊 Total videos: {len(all_uploads)}")
    print()

    # Confirm
    if not args.dry_run:
        print("=" * 70)
        response = input("Proceed with uploads? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("❌ Upload cancelled by user.")
            sys.exit(0)
        print("=" * 70)
        print()

    # Upload all videos with smart quota handling
    print("🚀 Starting uploads...")
    print()

    schedule_hours = 0
    successful = 0
    failed = 0
    quota_retries = 0

    idx = 0
    while idx < len(all_uploads):
        video_file, day_num, game_mode = all_uploads[idx]

        print("=" * 70)
        print(f"📹 Upload {idx + 1}/{len(all_uploads)}: {video_file.name}")
        print("=" * 70)

        success, quota_hit = upload_video(
            video_path=video_file,
            day=day_num,
            game_mode=game_mode,
            schedule_hours=schedule_hours,
            privacy=args.privacy,
            dry_run=args.dry_run
        )

        if quota_hit:
            print()
            print("⚠️" * 30)
            print("⚠️  YOUTUBE QUOTA LIMIT REACHED")
            print("⚠️" * 30)
            print()
            print(f"📊 Progress: {successful}/{len(all_uploads)} videos uploaded")
            print(f"⏰ Sleeping for {args.quota_sleep_hours} hours...")
            print(f"🔄 Will retry this video: {video_file.name}")
            print()

            # Save progress
            save_progress(idx, schedule_hours, progress_file)
            print(f"💾 Progress saved to: {progress_file}")
            print()

            if quota_retries >= QUOTA_MAX_RETRIES:
                print(f"❌ Maximum quota retries reached ({QUOTA_MAX_RETRIES})")
                print("   Please resume manually later")
                break

            quota_retries += 1

            # Sleep
            sleep_seconds = args.quota_sleep_hours * 3600
            wake_time = datetime.now() + timedelta(seconds=sleep_seconds)
            print(f"💤 Sleeping until {wake_time.strftime('%Y-%m-%d %H:%M:%S')}")

            if not args.dry_run:
                time.sleep(sleep_seconds)

            print()
            print("⏰ Waking up... Retrying upload")
            print()
            # Don't increment idx - retry same video
            continue

        if success:
            successful += 1
            print(f"✅ Upload successful ({successful}/{len(all_uploads)} completed)")
            quota_retries = 0  # Reset retry counter on success
        else:
            failed += 1
            print(f"❌ Upload failed ({failed} failures so far)")

        print()

        # Move to next video
        idx += 1
        schedule_hours += args.spacing_hours

        # Save progress
        save_progress(idx, schedule_hours, progress_file)

    # Final summary
    print("=" * 70)
    print("📊 BATCH UPLOAD SUMMARY")
    print("=" * 70)
    print(f"Total videos: {len(all_uploads)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    if args.dry_run:
        print("\n🧪 This was a dry run - no actual uploads occurred")
    else:
        print(f"\n🎬 Videos will publish over the next {schedule_hours - args.spacing_hours} hours")
        print("   Check YouTube Studio to manage scheduled videos")

        # Clean up progress file on complete success
        if successful == len(all_uploads):
            progress_file.unlink(missing_ok=True)
            print("\n✅ All uploads complete! Progress file cleaned up.")

    print("=" * 70)


if __name__ == "__main__":
    main()
