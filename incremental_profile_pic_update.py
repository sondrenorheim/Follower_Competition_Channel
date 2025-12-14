"""
Incremental Profile Picture Update System
Only fetches profile pictures for NEW followers (not in previous file)
Perfect for daily updates when you get new followers
"""

import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from typing import Set, List, Dict, Optional

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    print("⚠️  BeautifulSoup not installed. Install with: pip install beautifulsoup4")
    BS4_AVAILABLE = False

# Configuration
BASELINE_FILE = "followers_safe_20251213_merged.json"  # Your existing followers with pics
NEW_FOLLOWERS_FILE = "followers_safe_20251213.json"    # Today's scraped followers (may not have pics)
OUTPUT_FILE = f"followers_updated_{datetime.now().strftime('%Y%m%d')}.json"

# Rate limiting for small batches (can be more aggressive)
MIN_DELAY = 2.0
MAX_DELAY = 4.0
TIMEOUT = 10

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def load_followers(filename: str) -> Dict[str, dict]:
    """Load followers and return as dictionary keyed by username"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            followers_dict = {item['username']: item for item in data}
            print(f"[LOADED] {len(followers_dict):,} followers from {filename}")
            return followers_dict
    except FileNotFoundError:
        print(f"[WARN] File not found: {filename} (treating as empty)")
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return {}


def save_followers(followers_dict: Dict[str, dict], filename: str):
    """Save followers dictionary to JSON file"""
    try:
        follower_list = list(followers_dict.values())
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(follower_list, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] {len(follower_list):,} followers to {filename}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save {filename}: {e}")
        return False


def find_new_followers(baseline: Dict[str, dict], new_list: Dict[str, dict]) -> List[str]:
    """Find usernames in new_list that aren't in baseline"""
    baseline_usernames = set(baseline.keys())
    new_usernames = set(new_list.keys())
    new_only = new_usernames - baseline_usernames
    return sorted(new_only)


def extract_profile_pic_from_html(html: str, username: str) -> Optional[str]:
    """Extract profile picture URL from Instagram profile page HTML"""
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Method 1: og:image meta tag
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        # Method 2: JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'image' in data:
                    return data['image']
            except:
                continue

        return None
    except Exception as e:
        return None


def fetch_profile_pic_url(username: str, session: requests.Session) -> Optional[str]:
    """Fetch profile picture URL for a username"""
    try:
        url = f"https://www.instagram.com/{username}/"
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT)

        if response.status_code == 200:
            return extract_profile_pic_from_html(response.text, username)
        elif response.status_code == 404:
            return None
        elif response.status_code == 429:
            print(f"      Rate limited! Waiting 30s...")
            time.sleep(30)
            return None
        else:
            return None

    except Exception as e:
        return None


def fetch_pics_for_new_followers(new_usernames: List[str], followers_dict: Dict[str, dict]):
    """Fetch profile pictures for new followers only"""
    if not new_usernames:
        print("\n✅ No new followers to fetch!")
        return

    print(f"\n📸 Fetching profile pictures for {len(new_usernames)} new followers...")
    print("="*60)

    session = requests.Session()
    success = 0
    failed = 0

    for i, username in enumerate(new_usernames, 1):
        print(f"[{i}/{len(new_usernames)}] {username:20s}", end=' ')

        pic_url = fetch_profile_pic_url(username, session)

        if pic_url:
            if username in followers_dict:
                followers_dict[username]['profile_pic_url'] = pic_url
            success += 1
            print("✅")
        else:
            failed += 1
            print("❌")

        # Rate limit
        if i < len(new_usernames):
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    print("="*60)
    print(f"✅ Success: {success}/{len(new_usernames)}")
    print(f"❌ Failed: {failed}/{len(new_usernames)}")


def main():
    """Main execution"""
    if not BS4_AVAILABLE:
        print("\n❌ BeautifulSoup4 required. Install: pip install beautifulsoup4")
        return

    print("\n" + "="*60)
    print("  INCREMENTAL PROFILE PICTURE UPDATE")
    print("="*60)
    print()

    # Step 1: Load baseline (existing followers with pics)
    print("Step 1: Loading baseline followers...")
    baseline = load_followers(BASELINE_FILE)

    # Step 2: Load new followers list
    print("\nStep 2: Loading new followers list...")
    new_followers = load_followers(NEW_FOLLOWERS_FILE)

    # Step 3: Find new followers
    print("\nStep 3: Finding new followers...")
    new_usernames = find_new_followers(baseline, new_followers)
    print(f"   Found {len(new_usernames)} NEW followers!")

    if not new_usernames:
        print("\n✅ No new followers to process!")
        print("   Baseline and new list are the same.")
        return

    # Show sample of new followers
    print(f"\n   Sample of new followers:")
    for username in new_usernames[:10]:
        print(f"      • {username}")
    if len(new_usernames) > 10:
        print(f"      ... and {len(new_usernames) - 10} more")

    # Estimate time
    estimated_minutes = len(new_usernames) * 3 / 60
    print(f"\n   Estimated time: ~{estimated_minutes:.1f} minutes")
    print()

    response = input("Fetch profile pictures for new followers? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Step 4: Merge baseline + new followers
    print("\nStep 4: Merging follower lists...")
    merged = baseline.copy()
    new_added = 0
    for username, data in new_followers.items():
        if username not in merged:
            new_added += 1
        merged[username] = data
    print(f"   Total followers after merge: {len(merged):,}")
    print(f"   New followers added: {new_added:,}")

    # Step 5: Fetch profile pics for new followers only
    print("\nStep 5: Fetching profile pictures...")
    fetch_pics_for_new_followers(new_usernames, merged)

    # Step 6: Save updated list
    print(f"\nStep 6: Saving updated follower list...")
    save_followers(merged, OUTPUT_FILE)

    # Summary
    print("\n" + "="*60)
    print("  UPDATE COMPLETE")
    print("="*60)
    print(f"📁 Output file: {OUTPUT_FILE}")
    print(f"👥 Total followers: {len(merged):,}")
    print(f"🆕 New this update: {len(new_usernames):,}")
    print()
    print("Next steps:")
    print(f"1. Rename as your daily file: followers_safe_{datetime.now().strftime('%Y%m%d')}.json")
    print(f"2. Update FOLLOWER_IMPORT_FILE in config.py")
    print(f"3. Run your game!")
    print()


if __name__ == "__main__":
    main()
