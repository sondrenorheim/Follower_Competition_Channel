import instaloader
import json
import time
from datetime import datetime
from instaloader.exceptions import QueryReturnedNotFoundException, TooManyRequestsException, ConnectionException

USERNAME = "followerbattlegrounds"

def fetch_followers():
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        max_connection_attempts=3,
        quiet=False
    )

    L.load_session_from_file(USERNAME)
    profile = instaloader.Profile.from_username(L.context, USERNAME)

    followers_data = []
    total_followers = profile.followers
    print(f"Total followers reported: {total_followers}")
    print("Starting safe fetch with cooldowns...")

    for idx, f in enumerate(profile.get_followers(), start=1):
        try:
            followers_data.append({
                "username": f.username,
                "profile_pic_url": f.profile_pic_url,
                "profile_url": f"https://instagram.com/{f.username}"
            })
        except QueryReturnedNotFoundException:
            print(f"Skipped user #{idx}: missing data")
            continue

        # Cooldown every request (be gentle)
        time.sleep(1.5)

        # Progress update every 20 followers
        if idx % 20 == 0:
            print(f"Collected {idx}/{total_followers}...")

        # Safety back-off every 200 followers
        if idx % 200 == 0:
            print("Large batch fetched, pausing for 90 seconds...")
            time.sleep(90)

    print(f"Done! Fetched {len(followers_data)} followers")

    filename = f"followers_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(followers_data, f, indent=2)

    print(f"Data saved to: {filename}")

if __name__ == "__main__":
    try:
        fetch_followers()
    except TooManyRequestsException:
        print("Hit rate limit! Try again in 1-3 hours.")
    except ConnectionException as e:
        print(f"Connection error: {e}. Wait and retry later.")
