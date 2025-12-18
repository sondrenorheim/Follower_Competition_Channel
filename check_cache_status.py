"""
Check Profile Picture Cache Status
====================================
Quick utility to check how many profile pictures are cached and ready to use.
"""

import json
import sys
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
FOLLOWER_FILE = "Followers/all_followers_fresh.json"
CACHE_DIR = Path("avatar_cache")


def check_cache_status():
    """Check and report cache status"""
    print("\n" + "="*60)
    print("  PROFILE PICTURE CACHE STATUS")
    print("="*60)
    print()

    # Load followers
    try:
        with open(FOLLOWER_FILE, 'r', encoding='utf-8') as f:
            followers = json.load(f)
    except Exception as e:
        print(f"❌ Error loading {FOLLOWER_FILE}: {e}")
        return

    # Count cache status
    total = len(followers)
    cached = 0
    missing = 0
    no_url = 0

    missing_list = []

    for follower in followers:
        username = follower.get('username', '')
        profile_pic_url = follower.get('profile_pic_url', '').strip()

        cache_file = CACHE_DIR / f"{username}.jpg"

        if cache_file.exists():
            cached += 1
        elif not profile_pic_url or profile_pic_url.startswith('http://via.placeholder.com'):
            no_url += 1
        else:
            missing += 1
            if len(missing_list) < 20:  # Track first 20 missing
                missing_list.append(username)

    # Calculate percentages
    total_with_url = total - no_url
    cache_percentage = (cached / total_with_url * 100) if total_with_url > 0 else 0

    # Report
    print(f"📊 Overall Statistics:")
    print(f"   Total followers: {total:,}")
    print(f"   Have profile URL: {total_with_url:,}")
    print(f"   No URL available: {no_url:,}")
    print()
    print(f"💾 Cache Status:")
    print(f"   ✅ Cached: {cached:,}")
    print(f"   ❌ Missing: {missing:,}")
    print(f"   📈 Coverage: {cache_percentage:.1f}%")
    print()

    # Calculate cache size
    if CACHE_DIR.exists():
        cache_files = list(CACHE_DIR.glob("*.jpg"))
        total_size = sum(f.stat().st_size for f in cache_files)
        total_mb = total_size / (1024 * 1024)
        print(f"💾 Disk Usage:")
        print(f"   Cache directory: {CACHE_DIR.absolute()}")
        print(f"   Files on disk: {len(cache_files):,}")
        print(f"   Total size: {total_mb:.1f} MB")
        print()

    # Status message
    if missing == 0:
        print("✅ All profile pictures are cached and ready to use!")
    else:
        print(f"⚠️  {missing:,} profile pictures need to be downloaded")
        print()
        print("To download missing pictures:")
        print("   python download_all_profile_pics.py")

        if missing_list:
            print()
            print(f"First {len(missing_list)} missing:")
            for username in missing_list:
                print(f"   - {username}")
            if missing > len(missing_list):
                print(f"   ... and {missing - len(missing_list):,} more")

    print()
    print("="*60)
    print()


if __name__ == "__main__":
    check_cache_status()
