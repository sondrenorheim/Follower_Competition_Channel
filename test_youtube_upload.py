#!/usr/bin/env python3
"""
Test YouTube Upload
Quick test script to verify YouTube upload functionality

Usage:
    python test_youtube_upload.py --video "Videos/Day_30/team_battle_day_30_youtube_short.mp4"
"""

import argparse
from pathlib import Path
from youtube_uploader import (
    _normalize_path,
    authenticate_youtube,
    generate_description,
    generate_tags,
    generate_title,
    upload_video,
)

def main():
    parser = argparse.ArgumentParser(description="Test a single upload against the YouTube Shorts channel.")
    parser.add_argument("--video", required=True, help="Path to test video")
    parser.add_argument("--day", type=int, default=1, help="Day number (default: 1)")
    parser.add_argument("--game", default="team_battle", help="Game mode (default: team_battle)")
    parser.add_argument("--platform", choices=["instagram", "youtube"], default="instagram", help="Metadata platform target")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private", help="Privacy status")
    parser.add_argument("--client-secret-path", help="Optional OAuth client secret path for the new channel")
    parser.add_argument("--token-path", help="Optional token cache path for the new channel")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return

    print("=" * 70)
    print("🧪 YOUTUBE UPLOAD TEST")
    print("=" * 70)
    print(f"Video: {video_path}")
    print(f"Game: {args.game}")
    print(f"Day: {args.day}")
    print(f"Privacy: {args.privacy}")
    print("=" * 70)

    # Authenticate
    print("\n🔐 Authenticating with YouTube...")
    youtube = authenticate_youtube(
        client_secret_path=_normalize_path(args.client_secret_path),
        token_path=_normalize_path(args.token_path),
    )

    # Generate metadata
    title = generate_title(args.game, args.day, args.platform)
    description = generate_description(args.game, args.day, args.platform)
    tags = generate_tags(args.game, args.day, args.platform)

    print(f"\n📝 Title: {title}")
    print(f"📝 Description preview: {description[:100]}...")
    print(f"📝 Tags ({len(tags)}): {', '.join(tags[:5])}...")

    # Upload
    print(f"\n🚀 Uploading to YouTube as {args.privacy}...")
    video_id = upload_video(
        youtube,
        video_path=str(video_path),
        title=title,
        description=description,
        publish_time=None,
        tags=tags,
        thumbnail_path=None,
        privacy=args.privacy
    )

    if video_id:
        print("\n" + "=" * 70)
        print("✅ TEST SUCCESSFUL")
        print("=" * 70)
        print(f"Video ID: {video_id}")
        print(f"URL: https://www.youtube.com/watch?v={video_id}")
        print("=" * 70)
        print("\n💡 Next steps:")
        print("   1. Check your YouTube channel to verify the upload")
        print("   2. Confirm the standalone title and description fit the new Shorts channel")
        print("   3. If successful, use the main upload workflow or schedule the next Short")
    else:
        print("\n❌ TEST FAILED - Check error messages above")

if __name__ == "__main__":
    main()
