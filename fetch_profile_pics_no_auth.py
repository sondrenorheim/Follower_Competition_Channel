"""
Fetch Profile Pictures Without Authentication
Uses public Instagram profile pages to extract profile picture URLs
No login required - works for public profiles only
"""

import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    print("⚠️  BeautifulSoup not installed. Install with: pip install beautifulsoup4")
    BS4_AVAILABLE = False

# Configuration
INPUT_FILE = "Followers/all_followers_fresh.json"
OUTPUT_FILE = f"followers_with_pics_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

# Rate limiting (VERY conservative to avoid blocks)
MIN_DELAY = 5.0  # Minimum seconds between requests (increased for safety)
MAX_DELAY = 10.0  # Maximum seconds between requests (increased for safety)
BATCH_SIZE = 50  # Save progress every N profiles (increased to save more frequently)
MAX_RETRIES = 2  # Retry failed requests
TIMEOUT = 10     # Request timeout in seconds

# User agent to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


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


def extract_profile_pic_from_html(html: str, username: str) -> Optional[str]:
    """
    Extract profile picture URL from Instagram profile page HTML

    Args:
        html: HTML content of profile page
        username: Instagram username

    Returns:
        Profile picture URL or None
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Method 1: Try meta tag (og:image)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        # Method 2: Try JSON-LD structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'image' in data:
                    return data['image']
            except:
                continue

        # Method 3: Look for profile picture in img tags
        img_tags = soup.find_all('img', alt=f"{username}'s profile picture")
        if img_tags:
            return img_tags[0].get('src')

        return None
    except Exception as e:
        print(f"      Error parsing HTML: {type(e).__name__}")
        return None


def fetch_profile_pic_url(username: str, session: requests.Session, retry_count: int = 0) -> Optional[str]:
    """
    Fetch profile picture URL from Instagram public profile

    Args:
        username: Instagram username
        session: Requests session for connection pooling
        retry_count: Current retry attempt

    Returns:
        Profile picture URL or None if failed
    """
    try:
        url = f"https://www.instagram.com/{username}/"
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT)

        # Check response status
        if response.status_code == 200:
            pic_url = extract_profile_pic_from_html(response.text, username)
            return pic_url

        elif response.status_code == 404:
            print(f"      Profile not found (404)")
            return None

        elif response.status_code == 429:
            # Rate limited - need longer wait
            if retry_count < MAX_RETRIES:
                wait_time = 30 * (retry_count + 1)
                print(f"      Rate limited! Waiting {wait_time}s... ({retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return fetch_profile_pic_url(username, session, retry_count + 1)
            print(f"      Rate limited after {MAX_RETRIES} retries")
            return None

        else:
            print(f"      HTTP {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      Timeout, retrying... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(5)
            return fetch_profile_pic_url(username, session, retry_count + 1)
        print(f"      Timeout after {MAX_RETRIES} retries")
        return None

    except Exception as e:
        print(f"      Error: {type(e).__name__}")
        return None


def fetch_all_profile_pictures(followers):
    """
    Fetch profile picture URLs for all followers

    Args:
        followers: List of follower dictionaries

    Returns:
        Updated followers list with profile_pic_url populated
    """
    if not BS4_AVAILABLE:
        print("[ERROR] BeautifulSoup4 is required. Install with: pip install beautifulsoup4")
        return followers

    print("\n" + "="*60)
    print("  PROFILE PICTURE FETCHER (No Auth Required)")
    print("="*60)
    print()
    print("ℹ️  This method:")
    print("   • Works for PUBLIC profiles only")
    print("   • Does NOT require login")
    print("   • Uses conservative rate limiting")
    print("   • Saves progress every 25 profiles")
    print()

    # Create session for connection pooling
    session = requests.Session()

    # Stats
    total = len(followers)
    success_count = 0
    fail_count = 0
    skip_count = 0
    rate_limited = False

    # Process each follower
    for i, follower in enumerate(followers, 1):
        username = follower.get('username', '')
        current_url = follower.get('profile_pic_url', '')

        # Skip if already has profile pic URL
        if current_url and current_url.strip() and not current_url.startswith('http://via.placeholder.com'):
            skip_count += 1
            if i % 100 == 0:
                print(f"[{i}/{total}] Skipped {username} (already has URL)")
            continue

        print(f"[{i}/{total}] Fetching: {username:20s}", end=' ')

        # Fetch profile pic URL
        pic_url = fetch_profile_pic_url(username, session)

        if pic_url:
            follower['profile_pic_url'] = pic_url
            success_count += 1
            consecutive_failures = 0  # Reset consecutive failure counter on success
            print(f"✅")
        else:
            fail_count += 1
            consecutive_failures = consecutive_failures + 1 if 'consecutive_failures' in locals() else 1
            print(f"❌")

            # Only warn if many consecutive failures AND we've had some successes before
            # This filters out private profiles vs actual rate limiting
            if consecutive_failures >= 20 and success_count > 10:
                print("\n⚠️  WARNING: Many consecutive failures after successful fetches!")
                print("   This may indicate rate limiting. Consider:")
                print("   1. Increasing MIN_DELAY and MAX_DELAY")
                print("   2. Using a VPN or different IP address")
                print("   3. Waiting a few hours before resuming")
                response = input("\nContinue anyway? (y/n): ")
                if response.lower() != 'y':
                    rate_limited = True
                    break
                consecutive_failures = 0  # Reset if user chooses to continue

        # Rate limiting (random delay to appear more human)
        if i < total:
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)

        # Save progress every BATCH_SIZE profiles
        if i % BATCH_SIZE == 0:
            print(f"\n[CHECKPOINT] Saving progress... ({i}/{total} processed)")
            save_followers(followers, OUTPUT_FILE)
            print()

    # Final summary
    print("\n" + "="*60)
    print("  FETCH COMPLETE" if not rate_limited else "  FETCH INTERRUPTED")
    print("="*60)
    print(f"Total followers: {total:,}")
    print(f"Processed: {success_count + fail_count:,}")
    print(f"✅ Successfully fetched: {success_count:,}")
    print(f"⏭️  Skipped (already had URL): {skip_count:,}")
    print(f"❌ Failed: {fail_count:,}")
    print(f"📁 Output file: {OUTPUT_FILE}")
    print("="*60)
    print()

    return followers


def main():
    """Main execution"""
    # Check dependencies
    if not BS4_AVAILABLE:
        print("\n❌ Missing required package!")
        print("Install with: pip install beautifulsoup4")
        return

    # Load existing followers
    followers = load_followers(INPUT_FILE)
    if not followers:
        return

    print(f"\n⚠️  IMPORTANT NOTES:")
    print(f"   • This will take ~{len(followers) * 4.5 / 3600:.1f} hours for {len(followers):,} followers")
    print(f"   • Only PUBLIC profiles will work")
    print(f"   • Private profiles will fail")
    print(f"   • Progress auto-saves every {BATCH_SIZE} profiles")
    print(f"   • You can stop (Ctrl+C) and resume anytime")
    print()

    response = input("Ready to start? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Fetch profile pictures
    updated_followers = fetch_all_profile_pictures(followers)

    # Save final results
    save_followers(updated_followers, OUTPUT_FILE)

    print("\n✅ Profile picture URLs have been fetched!")
    print(f"📁 Output saved to: {OUTPUT_FILE}")
    print()
    print("Next steps:")
    print(f"1. Set DOWNLOAD_PROFILE_PICTURES = True in config.py")
    print(f"2. Set FOLLOWER_IMPORT_FILE = '{OUTPUT_FILE}' in config.py")
    print(f"3. Run your game - pictures will download from cached URLs")
    print()


if __name__ == "__main__":
    main()
