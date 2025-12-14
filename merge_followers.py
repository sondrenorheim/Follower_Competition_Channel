"""
Merge Two Follower JSON Files
Combines followers from two files, removes duplicates, saves result
"""

import json
from datetime import datetime

# Files to merge
FILE1 = "followers_safe_20251212 - Copy.json"  # Old 8k followers
FILE2 = "followers_safe_20251212.json"  # New 3k followers
OUTPUT_FILE = "followers_safe_merged.json"


def load_followers(filename):
    """Load followers from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[LOADED] {len(data):,} followers from {filename}")
            return {item['username']: item for item in data}
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filename}")
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to load {filename}: {e}")
        return {}


def merge_followers(followers1, followers2):
    """Merge two follower dictionaries, removing duplicates"""
    print("\n[MERGE] Merging follower data...")

    # Start with first set
    merged = followers1.copy()

    # Add from second set (overwrites if username exists)
    new_count = 0
    for username, data in followers2.items():
        if username not in merged:
            new_count += 1
        merged[username] = data

    print(f"[MERGE] File 1: {len(followers1):,} followers")
    print(f"[MERGE] File 2: {len(followers2):,} followers")
    print(f"[MERGE] New unique from File 2: {new_count:,}")
    print(f"[MERGE] Total unique followers: {len(merged):,}")

    return merged


def save_followers(followers, filename):
    """Save merged followers to JSON file"""
    follower_list = list(followers.values())

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(follower_list, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] {len(follower_list):,} followers saved to {filename}")


def main():
    print("="*60)
    print("  FOLLOWER MERGER")
    print("="*60)
    print()

    # Load both files
    followers1 = load_followers(FILE1)
    followers2 = load_followers(FILE2)

    if not followers1 and not followers2:
        print("[ERROR] No followers to merge!")
        return

    # Merge
    merged = merge_followers(followers1, followers2)

    # Save
    save_followers(merged, OUTPUT_FILE)

    print()
    print("="*60)
    print("  MERGE COMPLETE")
    print("="*60)
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Total unique followers: {len(merged):,}")
    print()


if __name__ == "__main__":
    main()
