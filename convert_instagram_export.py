"""
Convert Instagram Data Export to Standard Follower Format
Extracts followers from Instagram's export JSON and converts to standard format
Automatically finds newest export folder
"""

import json
import glob
from pathlib import Path
from datetime import datetime

# Configuration
FOLLOWERS_BASE_DIR = Path("Followers")
OUTPUT_FILE = FOLLOWERS_BASE_DIR / "all_followers.json"
CONNECTIONS_SUBPATH = "connections/followers_and_following"


def find_newest_export_folder():
    """Find the newest Instagram export folder"""
    if not FOLLOWERS_BASE_DIR.exists():
        print(f"❌ Followers directory not found: {FOLLOWERS_BASE_DIR}")
        return None

    # Get all subdirectories
    folders = [f for f in FOLLOWERS_BASE_DIR.iterdir() if f.is_dir()]

    if not folders:
        print(f"❌ No export folders found in {FOLLOWERS_BASE_DIR}")
        return None

    # Sort by modification time (newest first)
    folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    newest = folders[0]
    print(f"[FOUND] Newest export folder: {newest.name}")
    return newest


def parse_instagram_export_file(filepath):
    """
    Parse a single Instagram export JSON file

    Args:
        filepath: Path to followers_N.json file

    Returns:
        List of follower dictionaries
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        followers = []
        for entry in data:
            # Each entry has string_list_data array
            string_list_data = entry.get('string_list_data', [])

            for item in string_list_data:
                username = item.get('value', '')
                href = item.get('href', '')
                timestamp = item.get('timestamp', 0)

                if username:
                    follower = {
                        'username': username,
                        'profile_url': href if href else f"https://instagram.com/{username}",
                        'profile_pic_url': '',
                        'timestamp': timestamp
                    }
                    followers.append(follower)

        return followers

    except Exception as e:
        print(f"⚠️  Error parsing {filepath.name}: {e}")
        return []


def extract_all_followers(export_folder):
    """
    Extract all followers from Instagram export folder

    Args:
        export_folder: Path to Instagram export folder

    Returns:
        List of unique follower dictionaries
    """
    # Look for followers JSON files
    followers_dir = export_folder / CONNECTIONS_SUBPATH
    if not followers_dir.exists():
        print(f"❌ Followers directory not found: {followers_dir}")
        return []

    # Find all followers_*.json files
    follower_files = sorted(followers_dir.glob("followers_*.json"))

    if not follower_files:
        print(f"❌ No followers_*.json files found in {followers_dir}")
        return []

    print(f"\n[FILES] Found {len(follower_files)} follower files:")
    for f in follower_files:
        print(f"   • {f.name}")

    # Parse all files
    all_followers = {}  # Use dict to avoid duplicates (keyed by username)

    for filepath in follower_files:
        print(f"\n[PARSING] {filepath.name}...", end=' ')
        followers = parse_instagram_export_file(filepath)
        print(f"OK - {len(followers)} followers")

        # Add to dictionary (automatically handles duplicates)
        for follower in followers:
            username = follower['username']
            if username not in all_followers:
                all_followers[username] = follower
            else:
                # Keep the one with newer timestamp
                if follower['timestamp'] > all_followers[username]['timestamp']:
                    all_followers[username] = follower

    return list(all_followers.values())


def save_followers(followers, output_file):
    """
    Save followers to JSON file in standard format

    Args:
        followers: List of follower dictionaries
        output_file: Path to output file
    """
    # Remove timestamp field for final output (keep standard format)
    clean_followers = []
    for f in followers:
        clean_followers.append({
            'username': f['username'],
            'profile_url': f['profile_url'],
            'profile_pic_url': f['profile_pic_url']
        })

    # Sort by username for consistency
    clean_followers.sort(key=lambda x: x['username'].lower())

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clean_followers, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] {len(clean_followers):,} unique followers to {output_file}")


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("  INSTAGRAM EXPORT CONVERTER")
    print("="*60)
    print()

    # Step 1: Find newest export folder
    print("Step 1: Finding newest Instagram export...")
    export_folder = find_newest_export_folder()
    if not export_folder:
        return

    # Step 2: Extract all followers
    print(f"\nStep 2: Extracting followers from export...")
    followers = extract_all_followers(export_folder)

    if not followers:
        print("❌ No followers found!")
        return

    print(f"\n[SUMMARY]")
    print(f"   Total unique followers: {len(followers):,}")

    # Step 3: Check if output file exists (merge if needed)
    if OUTPUT_FILE.exists():
        print(f"\n[WARN] Output file already exists: {OUTPUT_FILE}")

        # ALWAYS create backup before any operation!
        from datetime import datetime
        backup_file = OUTPUT_FILE.parent / f"all_followers_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import shutil
        shutil.copy2(OUTPUT_FILE, backup_file)
        print(f"   ✅ Backup created: {backup_file.name}")

        print(f"\n   Do you want to:")
        print(f"   1. Overwrite (replace existing file) - NOT RECOMMENDED if you have profile pics!")
        print(f"   2. Smart Merge (SAFE - preserves ALL profile_pic_url data)")
        print(f"   3. Cancel")

        choice = input("\nEnter choice (1/2/3): ").strip()

        if choice == "2":
            # SAFE MERGE: Always preserve profile_pic_url from existing
            print("\n[SMART MERGE] Loading existing followers...")
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)

                # Count existing profile pics
                existing_with_pics = sum(1 for f in existing if f.get('profile_pic_url', ''))
                print(f"   Existing followers: {len(existing):,}")
                print(f"   Existing with profile pics: {existing_with_pics:,}")

                existing_dict = {f['username']: f for f in existing}

                # SMART MERGE: Add new followers, preserve profile_pic_urls
                new_count = 0
                for follower in followers:
                    username = follower['username']
                    if username not in existing_dict:
                        # New follower - add it
                        existing_dict[username] = {
                            'username': follower['username'],
                            'profile_url': follower['profile_url'],
                            'profile_pic_url': follower.get('profile_pic_url', '')
                        }
                        new_count += 1
                    else:
                        # Existing follower - UPDATE profile_url but PRESERVE profile_pic_url!
                        existing_dict[username]['profile_url'] = follower['profile_url']
                        # CRITICAL: Never overwrite profile_pic_url with empty value!
                        if not existing_dict[username].get('profile_pic_url', '') and follower.get('profile_pic_url', ''):
                            existing_dict[username]['profile_pic_url'] = follower['profile_pic_url']

                followers = list(existing_dict.values())

                # Verify we didn't lose any profile pics
                final_with_pics = sum(1 for f in followers if f.get('profile_pic_url', ''))
                print(f"\n   ✅ MERGE VALIDATION:")
                print(f"      New followers from export: {new_count:,}")
                print(f"      Total after merge: {len(followers):,}")
                print(f"      Profile pics BEFORE merge: {existing_with_pics:,}")
                print(f"      Profile pics AFTER merge: {final_with_pics:,}")

                if final_with_pics < existing_with_pics:
                    print(f"\n   ⚠️  ERROR: Lost {existing_with_pics - final_with_pics} profile pics!")
                    print(f"      Merge aborted. Your data is safe in backup: {backup_file.name}")
                    return
                else:
                    print(f"      ✅ All profile pics preserved!")

            except Exception as e:
                print(f"❌ Error during merge: {e}")
                print(f"   Your original data is safe in backup: {backup_file.name}")
                return

        elif choice == "3":
            print("Cancelled. Backup retained.")
            return
        elif choice == "1":
            # Warn about overwrite
            existing_with_pics = 0
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    existing_with_pics = sum(1 for f in existing if f.get('profile_pic_url', ''))
            except:
                pass

            if existing_with_pics > 0:
                print(f"\n   ⚠️  WARNING: Existing file has {existing_with_pics:,} profile pics!")
                confirm = input(f"   Are you SURE you want to overwrite? (yes/no): ").strip().lower()
                if confirm != "yes":
                    print("   Cancelled. Backup retained.")
                    return
                print(f"   Overwriting... (backup saved to {backup_file.name})")

    # Step 4: Save
    print(f"\nStep 3: Saving followers...")
    save_followers(followers, OUTPUT_FILE)

    # Final summary
    print("\n" + "="*60)
    print("  CONVERSION COMPLETE")
    print("="*60)
    print(f"[FILE] {OUTPUT_FILE}")
    print(f"[COUNT] Total followers in all_followers.json: {len(followers):,}")
    print()
    print("Next steps:")
    print(f"1. This file has NO profile pictures yet")
    print(f"2. Use this as your new BASELINE_FILE")
    print(f"3. Run profile picture fetcher:")
    print(f"   python fetch_profile_pics_no_auth.py")
    print()


if __name__ == "__main__":
    main()
