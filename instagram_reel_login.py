#!/usr/bin/env python3
"""
Create an instagrapi session JSON for a specific Instagram account.
Use this once per account, then point IG_SESSION_FILE (or --session-file in the uploader)
to the generated JSON for passwordless uploads.

Usage:
    python instagram_reel_login.py --username YOUR_USERNAME [--session-file session.json]
You will be prompted for password (and 2FA code if enabled).
"""

import argparse
import getpass
from pathlib import Path

from instagrapi import Client


def parse_args():
    parser = argparse.ArgumentParser(description="Create instagrapi session JSON for an account.")
    parser.add_argument("--username", required=True, help="Instagram username to log in as.")
    parser.add_argument(
        "--session-file",
        type=Path,
        default=Path("instagrapi_session.json"),
        help="Path to write the session JSON (default: instagrapi_session.json).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    password = getpass.getpass(f"Password for {args.username}: ")

    cl = Client()
    try:
        cl.login(args.username, password)
    except Exception as e:
        # Handle 2FA if needed
        if "challenge_required" in str(e) or "two_factor" in str(e):
            two_factor_code = input("Enter 2FA code: ").strip()
            cl.two_factor_login(two_factor_code)
        else:
            raise

    cl.dump_settings(args.session_file)
    print(f"✅ Session saved to {args.session_file}")
    print("Set IG_SESSION_FILE to this path for uploads, e.g.:")
    print(f"  set IG_SESSION_FILE={args.session_file}")


if __name__ == "__main__":
    main()
