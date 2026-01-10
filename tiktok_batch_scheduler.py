"""
Batch uploader/scheduler for TikTok videos using the existing TikTokAutoUploader lib.

Usage example:
  python tiktok_batch_scheduler.py ^
      --session-user myaccount ^
      --folder "VideosDirPath" ^
      --start-delay 1200 ^
      --spacing 1800 ^
      --visibility 0

Notes:
- The TikTokAutoUploader/login flow must have been run already to create
  a cookie file named `tiktok_session-<session-user>.cookie` in CookiesDir/.
- TikTok scheduling rules: schedule_time must be between 900s (15m) and 864000s (10 days).
  We enforce that per upload.
"""

import argparse
import sys
import re
from pathlib import Path

# Make sure we can import the bundled TikTok uploader
ROOT = Path(__file__).resolve().parent
TIKTOK_LIB = ROOT / "TiktokAutoUploader"
if str(TIKTOK_LIB) not in sys.path:
    sys.path.insert(0, str(TIKTOK_LIB))

from tiktok_uploader.tiktok import upload_video  # type: ignore


def is_video(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"}

def extract_day_number(path: Path) -> int | None:
    """Extract day number from path parts or filename (e.g., Day_26)."""
    pattern = re.compile(r"day[_ -]?(\d+)", re.IGNORECASE)
    # Check file name then parent dirs (closest first)
    candidates = [path.stem] + [p.name for p in path.parents]
    for text in candidates:
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    return None


def main():
    parser = argparse.ArgumentParser(description="Batch upload/schedule TikTok videos from a folder.")
    parser.add_argument("--session-user", required=True, help="Session user prefix used for the saved cookie (tiktok_session-<user>.cookie).")
    parser.add_argument("--folder", help="Single folder containing videos to upload/schedule.")
    parser.add_argument("--folders", nargs="+", help="One or more folders to process in order (overrides --folder).")
    parser.add_argument("--start-delay", type=int, default=0, help="Seconds from now for the first video (0 = immediate).")
    parser.add_argument("--spacing", type=int, default=0, help="Seconds between each scheduled video (0 = same time as first).")
    parser.add_argument("--visibility", type=int, default=0, choices=[0, 1], help="0=Public, 1=Private (private cannot be scheduled).")
    parser.add_argument("--allow-comment", type=int, default=1, choices=[0, 1], help="Allow comments (1 default).")
    parser.add_argument("--allow-duet", type=int, default=0, choices=[0, 1], help="Allow duet.")
    parser.add_argument("--allow-stitch", type=int, default=0, choices=[0, 1], help="Allow stitch.")
    parser.add_argument(
        "--title-template",
        default="Day {day} of making my followers fight each other 🥊 Follow to join the battle!\n#followerbattlegrounds #battle",
        help="Title template (use {day} placeholder).",
    )
    parser.add_argument("--default-day", type=int, default=None, help="Fallback day number if none found in path.")
    args = parser.parse_args()

    if args.folders:
        folder_list = [Path(p).expanduser().resolve() for p in args.folders]
    elif args.folder:
        folder_list = [Path(args.folder).expanduser().resolve()]
    else:
        raise SystemExit("Provide --folder or --folders.")

    videos = []
    for folder in folder_list:
        if not folder.exists() or not folder.is_dir():
            raise SystemExit(f"Folder not found: {folder}")
        folder_videos = sorted(p for p in folder.iterdir() if p.is_file() and is_video(p))
        if not folder_videos:
            print(f"No video files found in {folder} (skipping)")
            continue
        print(f"Found {len(folder_videos)} video(s) in {folder}")
        videos.extend(folder_videos)

    if not videos:
        raise SystemExit("No video files found in any provided folder.")

    for idx, video in enumerate(videos):
        schedule_time = args.start_delay + idx * args.spacing
        # TikTok requires schedule_time >= 900s; otherwise upload immediately
        if schedule_time < 900:
            schedule_time_effective = 0
        else:
            schedule_time_effective = schedule_time

        day_number = extract_day_number(video) or args.default_day
        if day_number is not None:
            title = args.title_template.format(day=day_number)
        else:
            title = video.stem.replace("_", " ")
        print(f"\n[{idx+1}/{len(videos)}] Uploading {video.name}")
        if schedule_time_effective > 0:
            print(f"  -> Scheduling in {schedule_time_effective} seconds")
        else:
            print("  -> Uploading immediately (schedule < 900s)")

        ok = upload_video(
            args.session_user,
            str(video),
            title,
            schedule_time_effective,
            args.allow_comment,
            args.allow_duet,
            args.allow_stitch,
            args.visibility,
        )
        if ok:
            print(f"  [OK] Success: {video.name}")
        else:
            print(f"  [FAILED] Failed: {video.name}")


if __name__ == "__main__":
    main()
