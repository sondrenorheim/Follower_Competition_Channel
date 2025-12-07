import instaloader
import json
import time
from datetime import datetime
from instaloader.exceptions import QueryReturnedNotFoundException, TooManyRequestsException

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

    # Load login session
    print("🔐 Loading session...")
    L.load_session_from_file(USERNAME)
    print("✅ Session loaded!")

    # Fetch profile
    print("📄 Getting profile info...")
    profile = instaloader.Profile.from_username(L.context, USERNAME)
    total = profile.followers
    print(f"👥 Total followers detected: {total}")

    followers_data = []
    print("🚦 Starting safe follower fetch with cooldowns...")

    for idx, follower in enumerate(profile.get_followers(), 1):
        try:
            followers_data.append({
                "username": follower.username,
                "profile_pic_url": follower.profile_pic_url,
                "profile_url": f"https://instagram.com/{follower.username}",
            })
        except QueryReturnedNotFoundException:
            print(f"⚠️ Missing data for follower #{idx}, skipping.")
            continue

        time.sleep(1.2)  # safe delay

        if idx % 20 == 0:
            print(f"📊 Progress: {idx}/{total}")

        if idx % 200 == 0:
            print("⏳ Cooling down for 60 seconds...")
            time.sleep(60)

    print(f"🎉 Done! Fetched {len(followers_data)} followers.")

    # Save JSON file
    filename = f"followers_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(followers_data, f, indent=2)

    print(f"📁 Saved to {filename}")
    return followers_data


if __name__ == "__main__":
    try:
        fetch_followers()
    except TooManyRequestsException:
        print("🚫 Instagram rate limit hit — wait 1–3 hours and try again.")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
