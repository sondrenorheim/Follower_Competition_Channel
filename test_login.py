import instaloader

USERNAME = "followerbattlegrounds"

print("Attempting to create new session...")
L = instaloader.Instaloader()

try:
    # Try to load existing session first
    L.load_session_from_file(USERNAME)
    print("✓ Existing session loaded successfully")

    # Test if we can access basic profile info
    profile = instaloader.Profile.from_username(L.context, USERNAME)
    print(f"✓ Profile accessible: @{profile.username}")
    print(f"  Followers: {profile.followers}")
    print(f"  Following: {profile.followees}")

    # Now try to access just ONE follower to test permissions
    print("\nTesting follower access...")
    followers = profile.get_followers()
    first_follower = next(followers)
    print(f"✓ Successfully accessed first follower: @{first_follower.username}")
    print("\n✓✓ Everything works! The issue might be transient.")

except instaloader.exceptions.ConnectionException as e:
    print(f"✗ Connection error: {e}")
    print("\nThis suggests Instagram is blocking follower access for this account/session.")
except instaloader.exceptions.QueryReturnedNotFoundException:
    print("✗ Profile not found or inaccessible")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    print("\nYou may need to login again interactively.")
    print("Run: python -c \"import instaloader; L = instaloader.Instaloader(); L.interactive_login('followerbattlegrounds'); L.save_session_to_file()\"")
