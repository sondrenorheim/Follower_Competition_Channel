"""
Test if your TikTok session is valid
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
session_file = PROJECT_ROOT / "tiktok_follower_account_sessionid.json"

print("Testing TikTok session...")
print(f"Session file: {session_file}\n")

if not session_file.exists():
    print("❌ Session file not found!")
    exit(1)

with open(session_file, 'r') as f:
    data = json.load(f)

session_id = data.get('sessionid', '')

if not session_id:
    print("❌ No sessionid found in file!")
    exit(1)

print(f"✓ Session ID found (length: {len(session_id)} chars)")
print(f"  First 20 chars: {session_id[:20]}...")
print(f"  Last 20 chars: ...{session_id[-20:]}\n")

# Try a simple test upload (you'll need a test video)
test_video = Path("Videos/Day_12/battle_royale_day_12.mp4")

if not test_video.exists():
    print(f"⚠️ Test video not found: {test_video}")
    print("   Session ID looks valid format-wise, but can't test upload without video")
    exit(0)

print(f"Testing upload with: {test_video.name}")

try:
    from TikTokUploader.uploader import uploadVideo

    print("Attempting test upload...")
    uploadVideo(
        session_id,
        str(test_video),
        "Test upload - will delete",
        [],  # tags
        [],  # mentions
        url_prefix="www"
    )
    print("✅ Upload test passed!")

except Exception as e:
    print(f"❌ Upload test failed: {e}")
    print("\nThis means:")
    print("  1. Session ID is expired/invalid - get a fresh one from browser")
    print("  2. TikTok is blocking automated uploads from your account")
    print("  3. Rate limiting - wait a few hours and try again")
