#!/usr/bin/env python3
"""
Batch YouTube Upload with Scheduling
Uploads all videos from Day folders sequentially with scheduled spacing.

Usage:
    # Start from Day 13, upload all videos with 2-hour spacing
    python batch_youtube_upload.py --start-day 13 --spacing-hours 2

    # Start from Day 13, end at Day 20, 3-hour spacing
    python batch_youtube_upload.py --start-day 13 --end-day 20 --spacing-hours 3

    # Dry run (show what would be uploaded without actually uploading)
    python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --dry-run

# Upload as unlisted instead of public
    python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --privacy unlisted
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
VIDEOS_ROOT = Path("Videos")
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}

# Game mode detection (from filename)
GAME_MODE_PATTERNS = {
    "battle_royale": "battle_royale",
    "fighter_arena": "fighter_arena",
    "team_battle": "team_battle",
    "obstacle_course": "obstacle_course",
    "platformer_race": "platformer_race",
    "snake_escape": "snake_escape",
    "spleef": "spleef",
    "anime_fighting": "anime_fighting",
    "followers_io": "followers_io",
}


def find_day_folders(start_day: int, end_day: int = None):
    """Find all Day_XX folders in the Videos directory."""
    day_folders = []

    if end_day is None:
        # Find all folders from start_day onwards
        for folder in sorted(VIDEOS_ROOT.glob("Day_*")):
            if folder.is_dir():
                try:
                    day_num = int(folder.name.split("_")[1])
                    if day_num >= start_day:
                        day_folders.append((day_num, folder))
                except (IndexError, ValueError):
                    continue
    else:
        # Find folders in range
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

        # Detect game mode from filename
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
    """Upload a single video to YouTube."""
    youtube_uploader = Path(__file__).parent / "youtube_uploader.py"

    if not youtube_uploader.exists():
        print(f"❌ YouTube uploader not found: {youtube_uploader}")
        return False

    if dry_run:
        publish_time = datetime.now() + timedelta(hours=schedule_hours)
        print(f"   [DRY RUN] Would upload: {video_path.name}")
        print(f"   [DRY RUN] Game: {game_mode}, Day: {day}")
        print(f"   [DRY RUN] Schedule: {schedule_hours}h ({publish_time.strftime('%Y-%m-%d %H:%M')})")
        print(f"   [DRY RUN] Privacy: {privacy}")
        return True

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
            errors='replace',  # Replace problematic characters instead of crashing
            timeout=600,
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            return True
        else:
            print(f"❌ Upload failed (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Upload timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Batch upload YouTube videos from Day folders with scheduled spacing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload from Day 13 onwards with 2-hour spacing
  python batch_youtube_upload.py --start-day 13 --spacing-hours 2

  # Upload Days 13-20 with 3-hour spacing as unlisted
  python batch_youtube_upload.py --start-day 13 --end-day 20 --spacing-hours 3 --privacy unlisted

  # Dry run to see what would be uploaded
  python batch_youtube_upload.py --start-day 13 --spacing-hours 2 --dry-run
        """
    )
    parser.add_argument("--start-day", type=int, required=True, help="Starting day number (e.g., 13)")
    parser.add_argument("--end-day", type=int, help="Ending day number (optional, if not set will process all available days)")
    parser.add_argument("--spacing-hours", type=int, default=2, help="Hours between each video upload (default: 2)")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="public", help="Privacy status (default: public)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded without actually uploading")
    parser.add_argument("--skip-on-error", action="store_true", help="Continue to next video if one fails (default: stop on error)")

    args = parser.parse_args()

    print("=" * 70)
    print("📹 BATCH YOUTUBE UPLOAD WITH SCHEDULING")
    print("=" * 70)
    print(f"Start Day: {args.start_day}")
    print(f"End Day: {args.end_day or 'All available'}")
    print(f"Spacing: {args.spacing_hours} hours between videos")
    print(f"Privacy: {args.privacy}")
    if args.dry_run:
        print("🧪 DRY RUN MODE - No actual uploads will occur")
    print("=" * 70)
    print()

    # Find all day folders
    day_folders = find_day_folders(args.start_day, args.end_day)

    if not day_folders:
        print(f"❌ No day folders found starting from Day {args.start_day}")
        print(f"   Looking in: {VIDEOS_ROOT.absolute()}")
        sys.exit(1)

    print(f"📂 Found {len(day_folders)} day folder(s):")
    for day_num, folder in day_folders:
        print(f"   - {folder.name}")
    print()

    # Collect all videos across all days
    all_uploads = []

    for day_num, folder in day_folders:
        videos = find_videos_in_folder(folder)

        if not videos:
            print(f"⚠️  No videos found in {folder.name}")
            continue

        print(f"📁 {folder.name}: Found {len(videos)} video(s)")
        for video_file, game_mode in videos:
            print(f"   - {video_file.name} ({game_mode})")
            all_uploads.append((video_file, day_num, game_mode))

    if not all_uploads:
        print("\n❌ No videos found to upload!")
        sys.exit(1)

    print()
    print("=" * 70)
    print(f"📊 UPLOAD SCHEDULE ({len(all_uploads)} videos total)")
    print("=" * 70)

    # Calculate schedule for each video
    current_time = datetime.now()
    schedule_hours = 0

    for idx, (video_file, day_num, game_mode) in enumerate(all_uploads):
        publish_time = current_time + timedelta(hours=schedule_hours)
        print(f"{idx + 1}. {video_file.name}")
        print(f"   Day: {day_num}, Game: {game_mode}")
        print(f"   Publish: {publish_time.strftime('%Y-%m-%d %H:%M')} ({schedule_hours}h from now)")
        print()
        schedule_hours += args.spacing_hours

    # Confirm before proceeding
    if not args.dry_run:
        print("=" * 70)
        response = input("Proceed with uploads? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("❌ Upload cancelled by user.")
            sys.exit(0)
        print("=" * 70)
        print()

    # Upload all videos
    print("🚀 Starting uploads...")
    print()

    schedule_hours = 0
    successful = 0
    failed = 0

    for idx, (video_file, day_num, game_mode) in enumerate(all_uploads):
        print("=" * 70)
        print(f"📹 Upload {idx + 1}/{len(all_uploads)}: {video_file.name}")
        print("=" * 70)

        success = upload_video(
            video_path=video_file,
            day=day_num,
            game_mode=game_mode,
            schedule_hours=schedule_hours,
            privacy=args.privacy,
            dry_run=args.dry_run
        )

        if success:
            successful += 1
            print(f"✅ Upload successful ({successful}/{len(all_uploads)} completed)")
        else:
            failed += 1
            print(f"❌ Upload failed ({failed} failures so far)")
            if not args.skip_on_error:
                print("\n⚠️  Stopping due to upload failure (use --skip-on-error to continue)")
                break

        print()
        schedule_hours += args.spacing_hours

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

    print("=" * 70)

    if failed > 0 and not args.skip_on_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
