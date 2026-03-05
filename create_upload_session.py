"""
Create a fresh Instagram session for uploading videos.
This session will be saved and can be reused by post_run_publish.py
"""
import getpass
import os
from pathlib import Path
from instagrapi import Client

USERNAME = "followerbattlegrounds"
PROJECT_ROOT = Path(__file__).resolve().parent

# Default session file location (same as post_run_publish.py expects)
DEFAULT_SESSION_PATH = PROJECT_ROOT / "sessions" / "session_followerbattlegrounds.json"

def create_session(session_file: Path = DEFAULT_SESSION_PATH):
    """Create a new Instagram session and save it to file."""

    print(f"Creating new Instagram session for @{USERNAME}")
    print(f"Session will be saved to: {session_file}\n")

    # Create directory if it doesn't exist
    session_file.parent.mkdir(parents=True, exist_ok=True)

    # Get password
    password = os.getenv('IG_PASSWORD')
    if not password:
        password = getpass.getpass(f"Password for @{USERNAME}: ")

    # Create client and login
    cl = Client()

    try:
        print("Logging in...")
        cl.login(USERNAME, password)
        print("✅ Login successful!")

        # Test the session
        print("Testing session...")
        cl.get_timeline_feed()
        print("✅ Session is valid!")

        # Save session
        cl.dump_settings(session_file)
        print(f"✅ Session saved to: {session_file}")
        print("\nYou can now use this session with:")
        print(f"  python post_run_publish.py --session-file \"{session_file}\"")
        print("\nOr just run:")
        print("  python post_run_publish.py")
        print("(since this is the default session file location)")

        return True

    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("\nPossible issues:")
        print("  1. Wrong password")
        print("  2. Two-factor authentication enabled (check your phone/email)")
        print("  3. Instagram flagged the login as suspicious")
        print("  4. Account may be temporarily restricted")
        return False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create Instagram session for uploading")
    parser.add_argument(
        "--session-file",
        type=Path,
        default=DEFAULT_SESSION_PATH,
        help="Path to save the session file"
    )
    args = parser.parse_args()

    success = create_session(args.session_file)
    exit(0 if success else 1)
