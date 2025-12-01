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

        # Delay before next upload (except after last one)
        if delay_seconds > 0 and idx < len(video_paths) - 1:
            print(f"⏳ Waiting {delay_seconds/3600:.2f} hours before next upload...")
            time.sleep(delay_seconds)


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
        default=None,
        help="Path to instagrapi session JSON (or set IG_SESSION_FILE env var).",
    )
    parser.add_argument(
        "--caption-template",
        default="Day {day_number} of making my followers battle every day! Follow to enter the battle 🥊\n\nCheck the link in the bio for your result and overall monthly ranking!\n\n#followerbattlegrounds",
        help="Caption template; placeholders: {game_mode}, {day_number}.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=int,
        default=0,
        help="Delay between uploads in seconds (default 0). Use 7200 for 2 hours.",
    )
    parser.add_argument(
        "--push-message",
        default=None,
        help="Optional git commit message for stats push.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    session_path = args.session_file or os.getenv("IG_SESSION_FILE")
    if not session_path:
        raise SystemExit("Missing session file. Provide --session-file or set IG_SESSION_FILE.")
    session_path = Path(session_path)

    # Build expected videos from ALL_GAME_MODES
    game_modes = getattr(config, "ALL_GAME_MODES", [])
    video_paths = [build_video_path(gm) for gm in game_modes]

    print("📦 Pushing stats/history to GitHub...")
    push_stats(args.push_message)

    print("📤 Uploading videos as Reels...")
    client = load_client(session_path)
    upload_videos(client, video_paths, args.caption_template, args.delay_seconds)
    print("✅ Done.")


if __name__ == "__main__":
    main()
