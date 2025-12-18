"""
Batch Profile Picture Fetcher - FREE Alternative to Apify
Uses multiple methods to fetch profile pics without paying $87
"""

import json
import time
import subprocess
import sys
from pathlib import Path

def load_usernames(filename="usernames_to_fetch.txt"):
    """Load usernames that need profile pics"""
    with open(filename, 'r', encoding='utf-8') as f:
        usernames = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(usernames):,} usernames")
    return usernames

def load_existing_data(filename="Followers/all_followers_fresh.json"):
    """Load existing follower data"""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data):,} existing followers")
    return {item['username']: item for item in data}

def save_data(followers_dict, filename="Followers/all_followers_fresh.json"):
    """Save updated follower data"""
    follower_list = list(followers_dict.values())

    # Backup first
    backup_file = filename.replace('.json', f'_backup_{time.strftime("%Y%m%d_%H%M%S")}.json')
    Path(filename).rename(backup_file)
    print(f"Backed up to: {backup_file}")

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(follower_list, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(follower_list):,} followers to {filename}")

def fetch_with_instaloader(usernames, batch_size=1000):
    """
    Use instaloader to fetch profile pics in batches
    This is MUCH faster than scraping HTML
    """
    print("\nMethod: Using Instaloader (Recommended)")
    print("="*60)

    # Check if instaloader is installed
    try:
        import instaloader
    except ImportError:
        print("Installing instaloader...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "instaloader"])
        import instaloader

    # Initialize
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False
    )

    # Try to load session
    session_file = "instaloader_session"
    if Path(session_file).exists():
        try:
            # Need to get username from session file
            print("Loading saved session...")
            # Read session file to get username
            with open(session_file, 'r') as f:
                for line in f:
                    if line.startswith('username='):
                        username = line.split('=')[1].strip()
                        L.load_session_from_file(username, session_file)
                        print(f"Session loaded for @{username}")
                        break
        except Exception as e:
            print(f"Could not load session: {e}")
            print("You may need to login...")

    # Load existing data
    followers_dict = load_existing_data()

    # Process usernames
    success = 0
    failed = 0

    for i, username in enumerate(usernames, 1):
        print(f"[{i}/{len(usernames)}] {username:20s}", end=' ')

        try:
            profile = instaloader.Profile.from_username(L.context, username)
            pic_url = profile.profile_pic_url

            if username in followers_dict:
                followers_dict[username]['profile_pic_url'] = pic_url
            else:
                followers_dict[username] = {
                    'username': username,
                    'profile_url': f'https://instagram.com/{username}',
                    'profile_pic_url': pic_url
                }

            success += 1
            print("✓")

            # Rate limiting
            time.sleep(2)  # 2 seconds between requests

            # Save progress every 50
            if i % 50 == 0:
                save_data(followers_dict)
                print(f"Progress saved ({i}/{len(usernames)})")

        except instaloader.exceptions.ProfileNotExistsException:
            failed += 1
            print("✗ (not found)")
        except instaloader.exceptions.LoginRequiredException:
            print("\n\nLogin required!")
            print("Run instaloader_follower_scraper.py first to setup session")
            break
        except Exception as e:
            failed += 1
            print(f"✗ ({type(e).__name__})")
            time.sleep(5)  # Longer delay on error

    # Final save
    save_data(followers_dict)

    print("\n" + "="*60)
    print(f"Success: {success:,} | Failed: {failed:,}")
    print("="*60)

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("  FREE PROFILE PIC FETCHER")
    print("  (No Apify costs!)")
    print("="*60)

    # Load usernames
    usernames = load_usernames()

    print(f"\nAbout to fetch profile pics for {len(usernames):,} users")
    print(f"Estimated time: ~{len(usernames) * 2 / 60:.0f} minutes")
    print(f"Cost: $0 (FREE!)")
    print()

    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return

    # Use instaloader method
    fetch_with_instaloader(usernames)

    print("\n✓ Done! Profile pics updated in Followers/all_followers_fresh.json")

if __name__ == "__main__":
    main()
