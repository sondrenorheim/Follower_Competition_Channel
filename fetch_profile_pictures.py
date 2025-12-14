"""
Fetch Profile Pictures for Existing Follower List
Takes a follower JSON file with usernames and fetches their profile pictures
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime

try:
    import instaloader
    INSTALOADER_AVAILABLE = True
except ImportError:
    print("⚠️  Instaloader not installed. Install with: pip install instaloader")
    INSTALOADER_AVAILABLE = False

# Configuration
INPUT_FILE = "followers_safe_20251213_merged.json"  # Input file with usernames
OUTPUT_FILE = f"followers_with_pics_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
AVATAR_CACHE_DIR = Path("avatar_cache")

# Rate limiting settings (be conservative to avoid blocks)
MIN_DELAY = 2.0  # Minimum seconds between requests
MAX_DELAY = 4.0  # Maximum seconds between requests
BATCH_SIZE = 50  # Save progress every N profiles
MAX_RETRIES = 3  # Retry failed requests


def load_followers(filename):
    """Load follower data from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[LOADED] {len(data):,} followers from {filename}")
            return data
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filename}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return []


def save_followers(followers, filename):
    """Save followers to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(followers, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] {len(followers):,} followers to {filename}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save {filename}: {e}")
        return False


def fetch_profile_pic_url_instaloader(L, username, retry_count=0):
    """
    Fetch profile picture URL using Instaloader

    Args:
        L: Instaloader instance
        username: Instagram username
        retry_count: Current retry attempt

    Returns:
        Profile picture URL or None if failed
    """
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return profile.profile_pic_url
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"      Profile not found: {username}")
        return None
    except instaloader.exceptions.ConnectionException as e:
        if retry_count < MAX_RETRIES:
            wait_time = (retry_count + 1) * 5
            print(f"      Connection error, retrying in {wait_time}s... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(wait_time)
            return fetch_profile_pic_url_instaloader(L, username, retry_count + 1)
        print(f"      Failed after {MAX_RETRIES} retries: {username}")
        return None
    except Exception as e:
        print(f"      Error fetching {username}: {type(e).__name__}")
        return None


def fetch_all_profile_pictures(followers, session_file=None):
    """
    Fetch profile picture URLs for all followers

    Args:
        followers: List of follower dictionaries
        session_file: Optional Instaloader session file for authentication

    Returns:
        Updated followers list with profile_pic_url populated
    """
    if not INSTALOADER_AVAILABLE:
        print("[ERROR] Instaloader is required. Install with: pip install instaloader")
        return followers

    print("\n" + "="*60)
    print("  PROFILE PICTURE FETCHER")
    print("="*60)
    print()

    # Create Instaloader instance
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True
    )

    # Try to load session if provided
    if session_file:
        try:
            # Extract username from session filename (e.g., "username" from session file)
            print(f"[AUTH] Loading session from: {session_file}")
            L.load_session_from_file(session_file)
            print("[AUTH] ✅ Session loaded successfully")
        except Exception as e:
            print(f"[AUTH] ⚠️  Failed to load session: {e}")
            print("[AUTH] Continuing without authentication (public profiles only)")

    # Stats
    total = len(followers)
    success_count = 0
    fail_count = 0
    skip_count = 0

    # Process each follower
    for i, follower in enumerate(followers, 1):
        username = follower.get('username', '')
        current_url = follower.get('profile_pic_url', '')

        # Skip if already has profile pic URL
        if current_url and current_url.strip():
            skip_count += 1
            if i % 100 == 0:
                print(f"[{i}/{total}] Skipped {username} (already has URL)")
            continue

        print(f"[{i}/{total}] Fetching: {username}", end='')

        # Fetch profile pic URL
        pic_url = fetch_profile_pic_url_instaloader(L, username)

        if pic_url:
            follower['profile_pic_url'] = pic_url
            success_count += 1
            print(f" ✅")
        else:
            fail_count += 1
            print(f" ❌")

        # Rate limiting
        if i < total:  # Don't delay after last request
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)

        # Save progress every BATCH_SIZE profiles
        if i % BATCH_SIZE == 0:
            print(f"\n[CHECKPOINT] Saving progress... ({i}/{total} processed)")
            save_followers(followers, OUTPUT_FILE)
            print()

    # Final summary
    print("\n" + "="*60)
    print("  FETCH COMPLETE")
    print("="*60)
    print(f"Total followers: {total:,}")
    print(f"✅ Successfully fetched: {success_count:,}")
    print(f"⏭️  Skipped (already had URL): {skip_count:,}")
    print(f"❌ Failed: {fail_count:,}")
    print(f"📁 Output file: {OUTPUT_FILE}")
    print("="*60)
    print()

    return followers


def main():
    """Main execution"""
    # Load existing followers
    followers = load_followers(INPUT_FILE)
    if not followers:
        return

    # Fetch profile pictures
    updated_followers = fetch_all_profile_pictures(followers)

    # Save final results
    save_followers(updated_followers, OUTPUT_FILE)

    print("\n✅ Profile picture URLs have been added to all followers!")
    print(f"📁 Output saved to: {OUTPUT_FILE}")
    print()
    print("Next steps:")
    print("1. Set DOWNLOAD_PROFILE_PICTURES = True in config.py")
    print("2. Set FOLLOWER_IMPORT_FILE = '{OUTPUT_FILE}' in config.py")
    print("3. Run your game - profile pictures will download automatically on first load")
    print()


if __name__ == "__main__":
    main()
