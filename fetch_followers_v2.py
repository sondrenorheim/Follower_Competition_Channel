"""
Alternative follower fetcher using instagrapi (mobile API)
More reliable than instaloader's web GraphQL approach
"""
import json
import time
from datetime import datetime

try:
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, RateLimitError
except ImportError:
    print("Installing instagrapi...")
    import subprocess
    subprocess.check_call(["pip", "install", "instagrapi"])
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, RateLimitError

USERNAME = "followerbattlegrounds"
# You'll need to set password as environment variable or enter it
# For security, don't hardcode passwords

def fetch_followers_v2():
    cl = Client()

    # Try to load session if it exists
    session_file = "instagrapi_session.json"
    try:
        cl.load_settings(session_file)
        print("Loaded existing session")
        cl.login(USERNAME, "")  # Empty password when using session
        cl.get_timeline_feed()  # Verify session works
        print("Session is valid!")
    except:
        print("No valid session found. Need to login...")
        print("Please set your password as environment variable 'IG_PASSWORD'")
        print("Or enter it when prompted:")
        import getpass
        import os
        password = os.getenv('IG_PASSWORD') or getpass.getpass("Password: ")

        cl.login(USERNAME, password)
        cl.dump_settings(session_file)
        print(f"Session saved to {session_file}")

    # Get account info
    user_id = cl.user_id_from_username(USERNAME)
    user_info = cl.user_info(user_id)
    total_followers = user_info.follower_count

    print(f"Total followers: {total_followers}")
    print("Fetching followers...")

    # Fetch followers (returns dict of user_id -> User objects)
    followers = cl.user_followers(user_id, amount=0)  # 0 = all followers

    followers_data = []
    for user_id, user in followers.items():
        followers_data.append({
            "username": user.username,
            "profile_pic_url": user.profile_pic_url,
            "profile_url": f"https://instagram.com/{user.username}",
            "full_name": user.full_name
        })

        # Progress update
        if len(followers_data) % 50 == 0:
            print(f"Collected {len(followers_data)}/{total_followers}...")

    print(f"Done! Fetched {len(followers_data)} followers")

    # Save to JSON
    filename = f"followers_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(followers_data, f, indent=2, ensure_ascii=False)

    print(f"Data saved to: {filename}")

    # Auto-update config.py to use the new file
    update_config_file(filename)

    return followers_data


def update_config_file(new_filename: str):
    """
    Update config.py to use the newly fetched followers file
    """
    import re

    config_path = "config.py"

    try:
        # Read config file
        with open(config_path, "r", encoding="utf-8") as f:
            config_content = f.read()

        # Find and replace FOLLOWER_IMPORT_FILE line
        # Pattern matches: FOLLOWER_IMPORT_FILE = "any_filename.json"
        pattern = r'(FOLLOWER_IMPORT_FILE\s*=\s*["\'])([^"\']+)(["\'])'

        # Check if pattern exists
        if re.search(pattern, config_content):
            # Replace with new filename
            new_content = re.sub(pattern, rf'\g<1>{new_filename}\g<3>', config_content)

            # Write back to config
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"✅ Updated config.py: FOLLOWER_IMPORT_FILE = \"{new_filename}\"")
        else:
            print(f"⚠️ Could not find FOLLOWER_IMPORT_FILE in config.py (manual update needed)")

    except FileNotFoundError:
        print(f"⚠️ config.py not found (manual update needed)")
    except Exception as e:
        print(f"⚠️ Failed to update config.py: {e} (manual update needed)")

if __name__ == "__main__":
    try:
        fetch_followers_v2()
    except RateLimitError:
        print("Rate limit hit! Wait 1-2 hours and try again.")
    except LoginRequired:
        print("Login failed or session expired. Delete instagrapi_session.json and try again.")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
