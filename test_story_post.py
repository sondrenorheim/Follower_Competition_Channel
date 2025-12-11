#!/usr/bin/env python3
"""
Test Story Posting Script
Posts an Instagram story for the current day's top 3 performers
"""

import sys
from pathlib import Path

# Import our modules
import config
from instagram_story_generator import generate_story_image, get_top_3_daily_performers
from safe_instagram_uploader import SafeInstagramUploader


def main():
    """Test posting a story for today's results"""

    # Get day number (use config or command line argument)
    day_number = config.DAY_NUMBER
    if len(sys.argv) > 1:
        day_number = int(sys.argv[1])

    print("=" * 60)
    print(f"INSTAGRAM STORY TEST - Day {day_number}")
    print("=" * 60)

    # Step 1: Get top 3 performers
    print(f"\nStep 1: Fetching top 3 performers for Day {day_number}...")
    top_3 = get_top_3_daily_performers(day_number)

    if not top_3:
        print("ERROR: No performers found for this day")
        print("Make sure game_history.json has results for this day")
        return False

    print(f"\nTop 3 performers:")
    for performer in top_3:
        print(f"  {performer['rank']}. {performer['username']}: {performer['total_points']:,} points")

    # Step 2: Generate story image
    print(f"\nStep 2: Generating story image...")
    story_path = f"test_story_day_{day_number}.png"

    if not generate_story_image(day_number, story_path):
        print("ERROR: Failed to generate story image")
        return False

    print(f"✓ Story image generated: {story_path}")

    # Step 3: Prepare usernames for tagging
    usernames_to_tag = [performer['username'] for performer in top_3]
    print(f"\nStep 3: Will tag {len(usernames_to_tag)} users:")
    for username in usernames_to_tag:
        print(f"  - @{username}")

    # Step 4: Confirm upload
    print(f"\n" + "=" * 60)
    print("Ready to upload story to Instagram!")
    print(f"Image: {story_path}")
    print(f"Tags: {', '.join(usernames_to_tag)}")
    print("=" * 60)

    response = input("\nProceed with upload? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("Upload cancelled by user")
        return False

    # Step 5: Upload story
    print(f"\nStep 5: Uploading story to Instagram...")
    print("NOTE: Browser will open (set headless=True to hide it)")

    uploader = SafeInstagramUploader(headless=False)  # Set False to watch it work

    success = uploader.upload_story(story_path, usernames_to_tag=usernames_to_tag)

    if success:
        print("\n" + "=" * 60)
        print("✓ SUCCESS: Story posted successfully!")
        print("=" * 60)
        print(f"\nThe story has been posted with:")
        print(f"- Top 3 performers displayed")
        print(f"- {len(usernames_to_tag)} users tagged")
        print("\nCheck your Instagram story to verify!")
        return True
    else:
        print("\n" + "=" * 60)
        print("✗ ERROR: Story upload failed")
        print("=" * 60)
        print("\nCheck the logs above for details")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
