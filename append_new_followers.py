"""
Append New Followers - Preserves Existing Data
Merges new Instagram export into existing follower list WITHOUT overwriting
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
# Path to latest Instagram export to merge in
NEW_EXPORT_DIR = r"C:\Users\SondreNorheim\Downloads\instagram-followerbattlegrounds-2025-12-19-5HTOPliS\connections\followers_and_following"
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


def append_from_export_dir(export_dir, existing_file=EXISTING_FILE, backup_file=None):
    if not backup_file:
        backup_file = f"Followers/all_followers_fresh_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    print("=" * 60)
    print("  APPEND NEW FOLLOWERS (PRESERVES EXISTING DATA)")
    print("=" * 60)

    # Step 1: Read existing followers
    existing_followers = {}
    if os.path.exists(existing_file):
        print()
        print(f"Reading existing file: {existing_file}")
        with open(existing_file, 'r', encoding='utf-8') as f:
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
        print()
        print(f"Creating backup: {backup_file}")
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(existing_list, f, indent=2, ensure_ascii=False)
    else:
        print()
        print(f"No existing file found at {existing_file}")
        print("Will create new file")

    # Step 2: Read new Instagram export files
    print()
    export_dir_path = Path(export_dir)
    if not export_dir_path.exists():
        print(f"  Export folder not found: {export_dir}")
        return None

    export_files = list(export_dir_path.glob("followers_*.json"))
    plain_followers = export_dir_path / "followers.json"
    if plain_followers.exists():
        export_files.append(plain_followers)

    if not export_files:
        fallback_dir = next(export_dir_path.rglob("followers_and_following"), None)
        if fallback_dir and fallback_dir != export_dir_path:
            export_dir_path = fallback_dir
            export_files = list(export_dir_path.glob("followers_*.json"))
            plain_followers = export_dir_path / "followers.json"
            if plain_followers.exists():
                export_files.append(plain_followers)
    print(f"Reading new export from: {export_dir_path}")

    def _export_sort_key(path: Path):
        match = re.search(r"followers_(\d+)\.json$", path.name, re.IGNORECASE)
        if match:
            return (0, int(match.group(1)))
        if path.name.lower() == "followers.json":
            return (1, 0)
        return (2, path.name.lower())

    export_files = sorted(export_files, key=_export_sort_key)
    if not export_files:
        print("  No followers_*.json files found in the export folder.")
        return None

    print(f"  Found {len(export_files)} follower file(s).")
    new_count = 0
    skipped_count = 0
    total_entries = 0

    for fpath in export_files:
        fname = fpath.name

        print()
        print(f"  Processing {fname}...")
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"    Entries in file: {len(data):,}")
        total_entries += len(data)

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

    print()
    print("=" * 60)
    print("MERGE COMPLETE:")
    print(f"  Total unique followers: {len(followers_list):,}")
    print(f"  New followers added: {new_count:,}")
    print(f"  Existing followers preserved: {skipped_count:,}")

    # Count profile pics
    with_pics = sum(1 for f in followers_list if f.get('profile_pic_url', ''))
    print(f"  With profile pics: {with_pics:,}")
    print(f"  Output: {existing_file}")
    print("=" * 60)
    if existing_followers and total_entries < (len(existing_followers) * 0.5):
        print("WARNING: Export contains far fewer entries than the existing list.")
        print("         Check the export date range or ensure the newest export was downloaded.")

    # Save
    os.makedirs(os.path.dirname(existing_file), exist_ok=True)
    with open(existing_file, 'w', encoding='utf-8') as f:
        json.dump(followers_list, f, indent=2, ensure_ascii=False)

    print()
    print(f"OK. Saved to: {existing_file}")
    print(f"OK. Backup saved to: {backup_file}")
    return {
        "total": len(followers_list),
        "new": new_count,
        "existing": skipped_count,
        "with_pics": with_pics,
        "output": existing_file,
        "backup": backup_file,
    }


def main():
    append_from_export_dir(NEW_EXPORT_DIR, EXISTING_FILE, BACKUP_FILE)


if __name__ == '__main__':
    main()
