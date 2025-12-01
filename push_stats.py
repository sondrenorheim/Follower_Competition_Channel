#!/usr/bin/env python3
"""
Manual stats push helper.
Run this after simulations to commit and push updated stats/history.
"""

import argparse
import sys

import config
from shared import auto_push


def main():
    parser = argparse.ArgumentParser(description="Push recorded stats/history to GitHub")
    parser.add_argument(
        "-m",
        "--message",
        help="Custom git commit message (optional)",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        help="Specific files to include (default: player_statistics.json, game_history.json)",
    )
    args = parser.parse_args()

    if getattr(config, "TEST_MODE", False):
        print("TEST_MODE is enabled; stats push skipped. Set TEST_MODE=False to push.")
        return 1

    success = auto_push.push_stats_to_github(
        files=args.files,
        commit_message=args.message,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
