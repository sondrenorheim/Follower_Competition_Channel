"""
Append New Followers - Preserves Existing Data
Merges new Instagram export into existing follower list WITHOUT overwriting
"""
import json
import os
from datetime import datetime

# Paths
# Path to latest Instagram export to merge in
NEW_EXPORT_DIR = r"C:\Users\SondreNorheim\Documents\Follower_Competition_Channel\Followers\instagram-followerbattlegrounds-2025-12-18-n8BsxrdB\connections\followers_and_following"
EXISTING_FILE = "Followers/all_followers_fresh.json"
BACKUP_FILE = f"Followers/all_followers_fresh_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

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
    print("  APPEND NEW FOLLOWERS (PRESERVES EXISTING DATA)")
    print("="*60)

    # Step 1: Read existing followers
    existing_followers = {}
    if os.path.exists(EXISTING_FILE):
        print(f"\nReading existing file: {EXISTING_FILE}")
        with open(EXISTING_FILE, 'r', encoding='utf-8') as f:
            existing_list = json.load(f)

        # Convert to dict for fast lookup, preserve all existing data
        for follower in existing_list:
            username = follower.get('username', '')
            if username:
                existing_followers[username] = follower

        print(f"  Existing followers: {len(existing_followers):,}")

        # Count how many have profile pics
        with_pics = sum(1 for f in existing_followers.values() if f.get('profile_pic_url', ''))
        print(f"  With profile pics: {with_pics:,}")

        # Create backup
        print(f"\nCreating backup: {BACKUP_FILE}")
        os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_list, f, indent=2, ensure_ascii=False)
    else:
        print(f"\nNo existing file found at {EXISTING_FILE}")
        print("Will create new file")

    # Step 2: Read new Instagram export files
    print(f"\nReading new export from: {NEW_EXPORT_DIR}")

    export_files = ['followers_1.json', 'followers_2.json', 'followers_3.json', 'followers_4.json']
    new_count = 0
    skipped_count = 0

    for fname in export_files:
        fpath = os.path.join(NEW_EXPORT_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  {fname} not found, skipping")
            continue

        print(f"\n  Processing {fname}...")
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"    Entries in file: {len(data):,}")

        for entry in data:
            follower = convert_instagram_entry(entry)
            if follower:
                username = follower['username']

                # Only add if NOT already in existing followers
                if username not in existing_followers:
                    existing_followers[username] = follower
                    new_count += 1
                else:
                    skipped_count += 1

    # Step 3: Convert to sorted list and save
    followers_list = sorted(existing_followers.values(), key=lambda x: x['username'].lower())

    print(f"\n{'='*60}")
    print(f"MERGE COMPLETE:")
    print(f"  Total unique followers: {len(followers_list):,}")
    print(f"  New followers added: {new_count:,}")
    print(f"  Existing followers preserved: {skipped_count:,}")

    # Count profile pics
    with_pics = sum(1 for f in followers_list if f.get('profile_pic_url', ''))
    print(f"  With profile pics: {with_pics:,}")
    print(f"  Output: {EXISTING_FILE}")
    print(f"{'='*60}")

    # Save
    os.makedirs(os.path.dirname(EXISTING_FILE), exist_ok=True)
    with open(EXISTING_FILE, 'w', encoding='utf-8') as f:
        json.dump(followers_list, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved to: {EXISTING_FILE}")
    print(f"✅ Backup saved to: {BACKUP_FILE}")

if __name__ == '__main__':
    main()
