"""
Instagram Follower Scraper using Instaloader
Fetches ALL followers using Instagram's API pagination
Automatically handles rate limiting and authentication
"""

import instaloader
import json
import time
from datetime import datetime
from pathlib import Path

# Configuration
TARGET_USERNAME = "followerbattlegrounds"  # The account to scrape followers from
LOGIN_USERNAME = ""  # Your burner account username (leave empty for first-time setup)
SESSION_FILE = "instaloader_session"  # Session file to persist login


def load_previous_followers(filename="followers_safe.json"):
    """Load previously scraped followers from file"""
    if Path(filename).exists():
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[LOADED] {len(data)} previous followers from {filename}")
            return {item['username']: item for item in data}
    else:
        print(f"[INFO] No previous follower file found at {filename}")
        return {}


def save_followers(followers, filename=None):
    """Save followers to JSON file"""
    if filename is None:
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"followers_safe_{date_str}.json"

    follower_list = list(followers.values())

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(follower_list, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] Saved to {filename}")
    return filename


def setup_instaloader():
    """Initialize Instaloader with session management"""
    L = instaloader.Instaloader(
        download_pictures=False,  # Don't download profile pictures (saves time)
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        max_connection_attempts=3
    )

    # Try to load existing session
    session_file_path = Path(SESSION_FILE)

    if session_file_path.exists():
        try:
            print(f"[INFO] Loading saved session from {SESSION_FILE}...")
            L.load_session_from_file(LOGIN_USERNAME, SESSION_FILE)
            print("[OK] Session loaded successfully!")
            return L
        except Exception as e:
            print(f"[WARN] Could not load session: {e}")
            print("[INFO] Will need to login again...")

    return L


def login_and_save_session(L):
    """Login to Instagram and save session for future use"""
    print("\n" + "="*60)
    print("  INSTAGRAM LOGIN REQUIRED")
    print("="*60)
    print("Enter your burner Instagram account credentials:")
    print("(These will be used to scrape followers)")
    print()

    username = input("Instagram Username: ").strip()
    password = input("Instagram Password: ").strip()

    print("\n[LOGIN] Logging in to Instagram...")

    try:
        L.login(username, password)
        print("[OK] Login successful!")

        # Save session for future use
        print(f"[SAVING] Saving session to {SESSION_FILE}...")
        L.save_session_to_file(SESSION_FILE)
        print("[OK] Session saved! You won't need to login next time.")

        global LOGIN_USERNAME
        LOGIN_USERNAME = username

        return True

    except instaloader.exceptions.BadCredentialsException:
        print("[ERROR] Invalid username or password!")
        return False
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        print("[ERROR] Two-factor authentication is enabled on this account.")
        print("[INFO] Please disable 2FA temporarily or use an account without 2FA.")
        return False
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return False


def warm_up_session(L, target_username):
    """
    Warm up the session by simulating normal Instagram behavior
    This helps avoid immediate rate limiting on fresh logins
    """
    print("\n[WARMUP] Simulating normal Instagram activity...")
    print("[WARMUP] This helps avoid rate limiting on fresh accounts...")

    try:
        # View target profile (normal behavior)
        profile = instaloader.Profile.from_username(L.context, target_username)
        print(f"[WARMUP] Viewed profile: @{target_username}")
        time.sleep(3)

        # View a few posts (simulate browsing)
        print("[WARMUP] Browsing recent posts...")
        post_count = 0
        for post in profile.get_posts():
            post_count += 1
            if post_count >= 3:  # View 3 posts
                break
            time.sleep(2)

        print(f"[WARMUP] Viewed {post_count} posts")

        # Wait a bit before scraping
        print("[WARMUP] Waiting 10 seconds before scraping followers...")
        time.sleep(10)

        print("[WARMUP] Warm-up complete! Starting follower scrape...")
        return True

    except Exception as e:
        print(f"[WARMUP] Warm-up failed (non-critical): {e}")
        print("[WARMUP] Proceeding anyway...")
        time.sleep(5)
        return False


def scrape_followers_with_instaloader(target_username):
    """
    Scrape all followers using Instaloader
    Handles pagination automatically
    """
    print("\n" + "="*60)
    print(f"  SCRAPING FOLLOWERS: @{target_username}")
    print("="*60)

    # Setup Instaloader
    L = setup_instaloader()

    # Check if we need to login
    fresh_login = False
    if not L.context.username:
        print("[INFO] No active session found. Login required.")
        if not login_and_save_session(L):
            print("[ERROR] Login failed. Cannot continue.")
            return []
        fresh_login = True

    # Warm up session if this was a fresh login
    if fresh_login:
        warm_up_session(L, target_username)

    try:
        # Get profile
        print(f"\n[INFO] Fetching profile: @{target_username}...")
        profile = instaloader.Profile.from_username(L.context, target_username)

        follower_count = profile.followers
        print(f"[INFO] Total followers reported by Instagram: {follower_count:,}")
        print(f"[INFO] Starting to fetch follower list...")
        print(f"[INFO] This may take a while for large accounts...")
        print()

        # Fetch all followers (with pagination)
        followers = {}
        count = 0
        start_time = time.time()

        for follower in profile.get_followers():
            count += 1

            followers[follower.username] = {
                "username": follower.username,
                "profile_url": f"https://instagram.com/{follower.username}",
                "profile_pic_url": follower.profile_pic_url,
            }

            # Progress update every 100 followers
            if count % 100 == 0:
                elapsed = time.time() - start_time
                rate = count / elapsed if elapsed > 0 else 0
                eta_seconds = (follower_count - count) / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60

                print(f"[PROGRESS] {count:,}/{follower_count:,} followers "
                      f"({count/follower_count*100:.1f}%) - "
                      f"Rate: {rate:.1f}/sec - "
                      f"ETA: {eta_minutes:.1f} min")

        print(f"\n[SUCCESS] Scraped {len(followers):,} followers!")

        elapsed_total = time.time() - start_time
        print(f"[TIME] Total time: {elapsed_total/60:.1f} minutes")

        return followers

    except instaloader.exceptions.ProfileNotExistsException:
        print(f"[ERROR] Profile @{target_username} does not exist!")
        return {}
    except instaloader.exceptions.LoginRequiredException:
        print("[ERROR] Login required but session expired. Please run again to re-login.")
        # Delete old session file
        Path(SESSION_FILE).unlink(missing_ok=True)
        return {}
    except instaloader.exceptions.ConnectionException as e:
        print(f"[ERROR] Connection error: {e}")
        print("[INFO] Instagram may be rate limiting. Try again later.")
        return {}
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def merge_followers(old_followers, new_followers):
    """Merge old and new follower data"""
    print("\n[MERGE] Merging follower data...")

    # Start with old followers
    merged = old_followers.copy()

    # Track statistics
    new_count = 0
    updated_count = 0

    for username, data in new_followers.items():
        if username not in merged:
            new_count += 1
            merged[username] = data
        else:
            # Update profile pic URL if changed
            if merged[username].get('profile_pic_url') != data.get('profile_pic_url'):
                updated_count += 1
            merged[username] = data

    print(f"[MERGE] Previous followers: {len(old_followers):,}")
    print(f"[MERGE] New unique followers: {new_count:,}")
    print(f"[MERGE] Updated follower data: {updated_count:,}")
    print(f"[MERGE] Total followers after merge: {len(merged):,}")

    return merged


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("  INSTAGRAM FOLLOWER SCRAPER (Instaloader)")
    print("="*60)
    print()

    # Load previous followers
    previous_followers = load_previous_followers()

    # Scrape followers using Instaloader
    new_followers = scrape_followers_with_instaloader(TARGET_USERNAME)

    if not new_followers:
        print("\n[ERROR] No followers scraped. Exiting without saving.")
        return

    # Merge with previous data
    merged_followers = merge_followers(previous_followers, new_followers)

    # Save to file
    filename = save_followers(merged_followers)

    print(f"\n[SUCCESS] Final follower count: {len(merged_followers):,}")
    print(f"[SUCCESS] Saved to: {filename}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Scraping interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
