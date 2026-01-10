#!/usr/bin/env python3
"""
Test YouTube Upload
Quick test script to verify YouTube upload functionality

Usage:
    python test_youtube_upload.py --video "Videos/Day_30/team_battle_day_30.mp4"
"""

import argparse
from pathlib import Path
from youtube_uploader import authenticate_youtube, upload_video, generate_tags, generate_title, generate_description

def main():
    parser = argparse.ArgumentParser(description="Test YouTube upload with a single video")
    parser.add_argument("--video", required=True, help="Path to test video")
    parser.add_argument("--day", type=int, default=1, help="Day number (default: 1)")
    parser.add_argument("--game", default="team_battle", help="Game mode (default: team_battle)")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private", help="Privacy status")
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
    youtube = authenticate_youtube()

    # Generate metadata
    title = generate_title(args.game, args.day)
    description = generate_description(args.game, args.day)
    tags = generate_tags(args.game, args.day)

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
        print("   2. If successful, you can now use the main upload workflow")
        print("   3. Run: python post_run_publish.py --youtube-privacy unlisted")
    else:
        print("\n❌ TEST FAILED - Check error messages above")

if __name__ == "__main__":
    main()
