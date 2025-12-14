"""
Fresh Instagram Export Merger
Merges all Instagram export files into a single clean follower list
"""
import json
import os
from pathlib import Path

# Paths
INSTAGRAM_EXPORT_DIR = r"C:\Users\SondreNorheim\Documents\Follower_Competition_Channel\Followers\instagram-followerbattlegrounds-2025-12-13-dg9RzcMr\connections\followers_and_following"
OUTPUT_FILE = "Followers/all_followers_fresh.json"

def convert_instagram_entry(entry):
    """Convert Instagram export format to our format"""
    try:
        string_data = entry.get('string_list_data', [])
        if not string_data:
            return None

        first_entry = string_data[0]
        username = first_entry.get('value', '')
        profile_url = first_entry.get('href', '')

        if not username:
            return None

        return {
            'username': username,
            'profile_url': profile_url,
            'profile_pic_url': ''  # Empty - to be filled by scraper
        }
    except Exception as e:
        print(f"Error converting entry: {e}")
        return None

def main():
    print("="*60)
    print("  FRESH INSTAGRAM EXPORT MERGER")
    print("="*60)

    # Read all Instagram export files
    all_followers = {}  # Use dict to deduplicate by username

    export_files = ['followers_1.json', 'followers_2.json', 'followers_3.json']

    for fname in export_files:
        fpath = os.path.join(INSTAGRAM_EXPORT_DIR, fname)
        if not os.path.exists(fpath):
            print(f"Warning: {fname} not found")
            continue

        print(f"\nProcessing {fname}...")
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"  Entries in file: {len(data):,}")

        for entry in data:
            follower = convert_instagram_entry(entry)
            if follower:
                username = follower['username']
                # Deduplicate - keep first occurrence
                if username not in all_followers:
                    all_followers[username] = follower

    # Convert to sorted list
    followers_list = sorted(all_followers.values(), key=lambda x: x['username'].lower())

    print(f"\n{'='*60}")
    print(f"MERGE COMPLETE:")
    print(f"  Unique followers: {len(followers_list):,}")
    print(f"  With profile pics: 0 (ready for scraping)")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"{'='*60}")

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(followers_list, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
