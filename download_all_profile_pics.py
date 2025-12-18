"""
Download and Cache All Profile Pictures
========================================
This script downloads profile pictures for all followers and caches them to disk.
Once cached, the pictures are available instantly for game runs without re-downloading.

Usage:
1. Ensure your Followers/all_followers_fresh.json has profile_pic_url populated
2. Run this script: python download_all_profile_pics.py
3. Profile pictures will be saved to avatar_cache/ directory
4. Future game runs will use cached images automatically
"""

import json
import sys
import time
import requests
from pathlib import Path
from PIL import Image
import io
import argparse
from typing import Dict, Optional
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io as io_module
    sys.stdout = io_module.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
FOLLOWER_FILE = "Followers/all_followers_fresh.json"
CACHE_DIR = Path("avatar_cache")
BATCH_SIZE = 100  # Save progress every N downloads
MIN_DELAY = 0.25  # Minimum seconds between downloads (to avoid rate limiting)
MAX_RETRIES = 5   # Retry failed downloads
TIMEOUT = 15      # Request timeout in seconds

# Stats tracking
stats = {
    "total": 0,
    "cached": 0,
    "downloaded": 0,
    "failed": 0,
    "no_url": 0,
    "start_time": None
}


def load_followers(filename: str) -> list:
    """Load follower data from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ Loaded {len(data):,} followers from {filename}")
            return data
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return []
    except Exception as e:
        print(f"❌ Failed to load {filename}: {e}")
        return []


def download_avatar(url: str, cache_path: Path, username: str) -> bool:
    """
    Download avatar image from URL and save to cache

    Args:
        url: Profile picture URL
        cache_path: Path to save cached image
        username: Username (for logging)

    Returns:
        True if successful, False otherwise
    """
    # Add headers to mimic a browser
    referer = 'https://www.tiktok.com/' if 'tiktok' in url.lower() else 'https://www.instagram.com/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Referer': referer
    }

    backoff = 0.5  # seconds
    for attempt in range(MAX_RETRIES):
        try:
            # Progressive timeout (longer for retries)
            timeout = TIMEOUT + (attempt * 5)

            # Exponential backoff for retries
            if attempt > 0:
                time.sleep(backoff * attempt)

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Load and convert image
            img = Image.open(io.BytesIO(response.content)).convert("RGBA")

            # Save as JPEG (smaller file size)
            rgb_img = img.convert('RGB')
            rgb_img.save(cache_path, 'JPEG', quality=85, optimize=True)

            return True

        except requests.exceptions.Timeout:
            if attempt >= MAX_RETRIES - 1:
                return False
            continue

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status in (403, 429) and attempt < MAX_RETRIES - 1:
                # Rate limited - wait longer
                time.sleep(2.0 * (attempt + 1))
                continue
            return False

        except Exception as e:
            return False

    return False


def download_all_profile_pictures(followers: list) -> Dict[str, int]:
    """
    Download and cache all profile pictures

    Args:
        followers: List of follower dictionaries

    Returns:
        Statistics dictionary
    """
    # Create cache directory
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*70)
    print("  PROFILE PICTURE CACHE BUILDER")
    print("="*70)
    print()
    print(f"📁 Cache directory: {CACHE_DIR.absolute()}")
    print(f"👥 Total followers: {len(followers):,}")
    print()

    stats["total"] = len(followers)
    stats["start_time"] = time.time()

    # Process each follower
    for i, follower in enumerate(followers, 1):
        username = follower.get('username', '')
        profile_pic_url = follower.get('profile_pic_url', '').strip()

        # Check if already cached
        cache_file = CACHE_DIR / f"{username}.jpg"
        if cache_file.exists():
            stats["cached"] += 1
            if i % 500 == 0:  # Less frequent logging for cached files
                print(f"[{i}/{stats['total']}] ✓ Cached: {username}")
            continue

        # Check if URL is available
        if not profile_pic_url or profile_pic_url.startswith('http://via.placeholder.com'):
            stats["no_url"] += 1
            if i % 100 == 0:
                print(f"[{i}/{stats['total']}] ⊘ No URL: {username}")
            continue

        # Download avatar
        print(f"[{i}/{stats['total']}] ⬇ Downloading: {username:25s}", end=' ')

        success = download_avatar(profile_pic_url, cache_file, username)

        if success:
            stats["downloaded"] += 1
            print("✅")
        else:
            stats["failed"] += 1
            print("❌")

        # Rate limiting
        if i < stats['total']:
            time.sleep(MIN_DELAY)

        # Progress checkpoint
        if i % BATCH_SIZE == 0:
            elapsed = time.time() - stats["start_time"]
            rate = i / elapsed if elapsed > 0 else 0
            remaining = stats["total"] - i
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_mins = eta_seconds / 60

            print()
            print(f"  ⏱️  Progress: {i:,}/{stats['total']:,} ({i/stats['total']*100:.1f}%)")
            print(f"  ⚡ Rate: {rate:.1f} followers/sec")
            print(f"  🕐 ETA: {eta_mins:.1f} minutes")
            print(f"  ✅ Downloaded: {stats['downloaded']:,} | ✓ Cached: {stats['cached']:,}")
            print(f"  ❌ Failed: {stats['failed']:,} | ⊘ No URL: {stats['no_url']:,}")
            print()

    # Calculate final stats
    elapsed_total = time.time() - stats["start_time"]
    elapsed_mins = elapsed_total / 60

    # Print final summary
    print("\n" + "="*70)
    print("  DOWNLOAD COMPLETE")
    print("="*70)
    print(f"📊 Statistics:")
    print(f"   Total followers: {stats['total']:,}")
    print(f"   ✅ Successfully downloaded: {stats['downloaded']:,}")
    print(f"   ✓  Already cached: {stats['cached']:,}")
    print(f"   ❌ Failed downloads: {stats['failed']:,}")
    print(f"   ⊘  No URL available: {stats['no_url']:,}")
    print()
    print(f"⏱️  Time elapsed: {elapsed_mins:.1f} minutes")
    print(f"📁 Cache location: {CACHE_DIR.absolute()}")
    print()

    # Calculate coverage
    total_with_url = stats['total'] - stats['no_url']
    successful = stats['downloaded'] + stats['cached']
    if total_with_url > 0:
        coverage = (successful / total_with_url) * 100
        print(f"📈 Cache coverage: {successful:,}/{total_with_url:,} ({coverage:.1f}%)")

    print("="*70)
    print()

    return stats


def verify_cache_quality():
    """
    Verify cached images are valid and report any issues
    """
    print("\n🔍 Verifying cache quality...")

    corrupted = []
    total_size = 0

    cache_files = list(CACHE_DIR.glob("*.jpg"))

    for cache_file in cache_files:
        try:
            # Try to open the image
            with Image.open(cache_file) as img:
                img.verify()

            # Track file size
            total_size += cache_file.stat().st_size

        except Exception as e:
            corrupted.append((cache_file.name, str(e)))

    if corrupted:
        print(f"\n⚠️  Found {len(corrupted)} corrupted cache files:")
        for filename, error in corrupted[:10]:  # Show first 10
            print(f"   - {filename}: {error}")
        if len(corrupted) > 10:
            print(f"   ... and {len(corrupted) - 10} more")
    else:
        print("✅ All cached images are valid!")

    # Report cache size
    total_mb = total_size / (1024 * 1024)
    print(f"💾 Total cache size: {total_mb:.1f} MB ({len(cache_files):,} files)")


def main():
    """Main execution"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download and cache profile pictures')
    parser.add_argument('--auto', action='store_true', help='Skip confirmation prompts')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  PROFILE PICTURE CACHE BUILDER")
    print("="*70)
    print()
    print("This script will:")
    print("  1. Load all followers from", FOLLOWER_FILE)
    print("  2. Download profile pictures for followers with URLs")
    print("  3. Cache them to disk in", CACHE_DIR)
    print("  4. Skip already-cached pictures (resume-friendly)")
    print()
    print("Once cached, game runs will load instantly from disk!")
    print()

    # Load followers
    followers = load_followers(FOLLOWER_FILE)
    if not followers:
        return

    # Count how many need downloading
    needs_download = 0
    already_cached = 0
    for follower in followers:
        username = follower.get('username', '')
        profile_pic_url = follower.get('profile_pic_url', '').strip()
        cache_file = CACHE_DIR / f"{username}.jpg"

        if cache_file.exists():
            already_cached += 1
        elif profile_pic_url and not profile_pic_url.startswith('http://via.placeholder.com'):
            needs_download += 1

    print(f"📊 Status:")
    print(f"   Total followers: {len(followers):,}")
    print(f"   Already cached: {already_cached:,}")
    print(f"   Need to download: {needs_download:,}")

    if needs_download == 0:
        print()
        print("✅ All profile pictures are already cached!")
        print()
        verify_cache_quality()
        return

    # Estimate time
    estimated_seconds = needs_download * (MIN_DELAY + 0.5)  # Download time + delay
    estimated_mins = estimated_seconds / 60

    print()
    print(f"⏱️  Estimated time: ~{estimated_mins:.1f} minutes")
    print()

    if not args.auto:
        response = input("Ready to start downloading? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    else:
        print("Auto mode: Starting download automatically...")
        print()

    # Download all profile pictures
    download_all_profile_pictures(followers)

    # Verify cache quality
    verify_cache_quality()

    print("\n✅ Profile picture cache is ready!")
    print()
    print("Next steps:")
    print("  1. Set LOAD_PROFILE_PICTURES = True in config.py")
    print("  2. Run your games - pictures will load instantly from cache!")
    print()


if __name__ == "__main__":
    main()
