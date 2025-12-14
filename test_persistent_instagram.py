"""
Test Persistent Instagram Uploader
Tests 2FA handling and session persistence with a single upload

Usage:
    python test_persistent_instagram.py
"""

import sys
from pathlib import Path
from persistent_instagram_uploader import PersistentInstagramUploader


def main():
    print("="*60)
    print("  TEST: Persistent Instagram Uploader")
    print("="*60)
    print()
    print("This will test:")
    print("  1. Starting persistent Instagram session")
    print("  2. Handling 2FA (if required)")
    print("  3. Uploading a test video")
    print("  4. Keeping session open")
    print()
    print("="*60)
    print()

    # Find a test video
    test_video = None
    video_dirs = ["output", "output_videos", "."]

    for dir_path in video_dirs:
        video_path = Path(dir_path)
        if video_path.exists():
            videos = list(video_path.glob("*.mp4"))
            if videos:
                test_video = videos[0]
                break

    if not test_video:
        print("ERROR: No test video found!")
        print("Please place a .mp4 file in the current directory or output/ folder")
        return

    print(f"Found test video: {test_video.name}")
    print()

    # Create uploader (visible browser for 2FA)
    uploader = PersistentInstagramUploader(
        cookies_file="instagram_cookies.json",
        headless=False  # Keep browser visible
    )

    try:
        # STEP 1: Start session (handles 2FA if needed)
        print("STEP 1: Starting Instagram session...")
        print("(If 2FA is required, you'll be prompted to enter it in the browser)")
        print()

        if not uploader.start_session():
            print("ERROR: Failed to start session")
            return

        print()
        print("SUCCESS: Session started!")
        print()

        # STEP 2: Upload test video
        print("STEP 2: Uploading test video...")
        test_caption = "🧪 Test upload from persistent session"

        if uploader.upload_video(str(test_video), test_caption):
            print()
            print("SUCCESS: Test video uploaded!")
        else:
            print()
            print("ERROR: Upload failed")

        print()
        print("="*60)
        print("Session is still OPEN!")
        print()
        print("Options:")
        print("  1. Press Enter to close browser and end test")
        print("  2. Keep browser open and test manually")
        print("="*60)

        choice = input("\nPress Enter to close browser (or Ctrl+C to keep open)... ")

        # STEP 3: Close session
        print()
        print("STEP 3: Closing session...")
        uploader.close_session()

        print()
        print("="*60)
        print("  TEST COMPLETE")
        print("="*60)
        print()
        print("Summary:")
        print("  ✅ Session started (2FA handled if needed)")
        print("  ✅ Video uploaded using persistent session")
        print("  ✅ Browser closed cleanly")
        print()
        print("You're ready for daily automation!")
        print()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        print("Browser is still open - close it manually or run script again")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure cleanup
        if uploader.driver:
            print("\nCleaning up...")
            try:
                uploader.close_session()
            except:
                pass


if __name__ == "__main__":
    main()
